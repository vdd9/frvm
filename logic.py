from bitarray import bitarray

"""
Boolean expression parser (electronic logic style):
  !  = NOT (explicitly marked NO)
  ?  = UNSET (neither YES nor NO)
  +  = OR  
  .  = AND (optional, concatenation implies AND)
  () = grouping

Examples:
  🥗           → videos with 🥗 (yes=1)
  !🥗          → videos without 🥗 (no=1)
  ?🥗          → videos where 🥗 is unset (neither yes nor no)
  🥗.🐈        → videos with 🥗 AND 🐈
  🥗🐈         → same (implicit AND)
  🥗+🐈        → videos with 🥗 OR 🐈
  🥗.!👎       → videos with 🥗 and explicitly without 👎
  🥗.?🔥       → videos with 🥗 where 🔥 is unset
  (🥗+🔥).💃   → (🥗 OR 🔥) AND 💃
"""


def tokenize(expr: str, categories: dict) -> list:
    """
    Transform expression into tokens.
    Possible tokens: 'NOT', 'AND', 'OR', '(', ')', ('EMOJI', emoji_str)
    """
    tokens = []
    i = 0
    expr = expr.replace(" ", "")  # remove spaces
    
    # Sort emojis by decreasing length
    sorted_emojis = sorted(categories.keys(), key=len, reverse=True)
    
    while i < len(expr):
        c = expr[i]
        
        if c == '!':
            # Implicit AND before NOT if previous token is EMOJI or )
            if tokens and (isinstance(tokens[-1], tuple) or tokens[-1] == ')'):
                tokens.append('AND')
            tokens.append('NOT')
            i += 1
        elif c == '?':
            # Implicit AND before UNSET if previous token is EMOJI or )
            if tokens and (isinstance(tokens[-1], tuple) or tokens[-1] == ')'):
                tokens.append('AND')
            tokens.append('UNSET')
            i += 1
        elif c == '+':
            tokens.append('OR')
            i += 1
        elif c == '.':
            tokens.append('AND')
            i += 1
        elif c == '(':
            # Implicit AND before ( if previous token is EMOJI or )
            if tokens and (isinstance(tokens[-1], tuple) or tokens[-1] == ')'):
                tokens.append('AND')
            tokens.append('(')
            i += 1
        elif c == ')':
            tokens.append(')')
            i += 1
        else:
            # Look for an emoji
            found = False
            for emoji in sorted_emojis:
                if expr[i:].startswith(emoji):
                    # Implicit AND if previous token is an emoji or )
                    if tokens and (isinstance(tokens[-1], tuple) or tokens[-1] == ')'):
                        tokens.append('AND')
                    tokens.append(('EMOJI', emoji))
                    i += len(emoji)
                    found = True
                    break
            
            if not found:
                raise ValueError(f"Unknown character at position {i}: '{expr[i:][:10]}'")
    
    return tokens


class Parser:
    """Recursive descent parser for boolean expressions."""
    
    def __init__(self, tokens: list, categories: dict):
        self.tokens = tokens
        self.pos = 0
        self.categories = categories
    
    def peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None
    
    def consume(self, expected=None):
        token = self.peek()
        if expected and token != expected:
            raise ValueError(f"Attendu {expected}, reçu {token}")
        self.pos += 1
        return token
    
    def parse(self) -> bitarray:
        """Entry point: parse the entire expression."""
        result = self.parse_or()
        if self.peek() is not None:
            raise ValueError(f"Remaining tokens: {self.tokens[self.pos:]}")
        return result
    
    def parse_or(self) -> bitarray:
        """expr_or → expr_and ('+' expr_and)*"""
        left = self.parse_and()
        while self.peek() == 'OR':
            self.consume('OR')
            right = self.parse_and()
            left = left | right
        return left
    
    def parse_and(self) -> bitarray:
        """expr_and → expr_not ('.' expr_not)* | expr_not expr_not (AND implicite)"""
        left = self.parse_not()
        while self.peek() == 'AND':
            self.consume('AND')
            right = self.parse_not()
            left = left & right
        return left
    
    def parse_not(self) -> bitarray:
        """expr_not → '!' expr_not | '?' expr_not | atom"""
        if self.peek() == 'NOT':
            self.consume('NOT')
            # ! before an emoji = look in the "no" bitarray
            # We need to know if an emoji follows
            token = self.peek()
            if isinstance(token, tuple) and token[0] == 'EMOJI':
                self.consume()
                emoji = token[1]
                return self.categories[emoji]["no"].copy()
            else:
                # NOT of a sub-expression
                inner = self.parse_not()
                return ~inner
        
        if self.peek() == 'UNSET':
            self.consume('UNSET')
            # ? before an emoji = neither yes nor no is set
            token = self.peek()
            if isinstance(token, tuple) and token[0] == 'EMOJI':
                self.consume()
                emoji = token[1]
                yes = self.categories[emoji]["yes"]
                no = self.categories[emoji]["no"]
                # UNSET = ~(yes | no) = neither marked yes nor marked no
                return ~(yes | no)
            else:
                # UNSET of a sub-expression doesn't really make sense,
                # but we'll interpret it as NOT
                inner = self.parse_not()
                return ~inner
        
        return self.parse_atom()
    
    def parse_atom(self) -> bitarray:
        """atom → EMOJI | '(' expr_or ')'"""
        token = self.peek()
        
        if token == '(':
            self.consume('(')
            result = self.parse_or()
            self.consume(')')
            return result
        
        if isinstance(token, tuple) and token[0] == 'EMOJI':
            self.consume()
            emoji = token[1]
            return self.categories[emoji]["yes"].copy()
        
        raise ValueError(f"Unexpected token: {token}")


def evaluate(expr: str, categories: dict) -> bitarray:
    """
    Evaluate a boolean expression on categories.
    
    Syntax:
      !  = NOT (before emoji: looks in "no", before expr: inverts)
      +  = OR
      .  = AND (optional, concatenation = implicit AND)
      () = grouping
    
    Args:
        expr: Expression like "🥗.!👎" or "🔥+💃"
        categories: dict[emoji, {"yes": bitarray, "no": bitarray}]
    
    Returns:
        bitarray with 1 for each matching video
    """
    if not categories:
        raise ValueError("No categories loaded")
    
    if not expr.strip():
        raise ValueError("Empty expression")
    
    tokens = tokenize(expr, categories)
    parser = Parser(tokens, categories)
    return parser.parse()
