from bitarray import bitarray

"""
Boolean expression parser (electronic logic style):
  !  = NOT (explicitly marked NO)
  ?  = UNSET (neither YES nor NO)
  +  = OR  
  .  = AND (optional, concatenation implies AND)
  () = grouping
  @  = performer prefix (e.g. @Sage_bd)
  !@ = admin explicitly said "no performers" (_none)
  ?@ = unset performers (admin hasn't tagged yet)

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
  @Sage_bd     → videos with performer Sage_bd
  🔞.@Sage_bd  → explicit videos with Sage_bd
  @Sage_bd+@livymae → videos with either performer
  !@           → videos explicitly marked as having no performers
  ?@           → videos where performers are unset (not tagged yet)
  !?@          → videos that have been tagged (either !@ or @someone)
  🔥.?@        → hot videos not yet tagged for performers
"""


def tokenize(expr: str, categories: dict, performers: dict = None) -> list:
    """
    Transform expression into tokens.
    Possible tokens: 'NOT', 'AND', 'OR', '(', ')', ('EMOJI', emoji_str), ('PERFORMER', name)
    """
    if performers is None:
        performers = {}
    tokens = []
    i = 0
    expr = expr.replace(" ", "")  # remove spaces
    
    # Sort emojis by decreasing length
    sorted_emojis = sorted(categories.keys(), key=len, reverse=True)
    # Sort performer names by decreasing length to match longest first
    # NOTE: be careful if one performer name is a substring of another (e.g. "mae" vs "livymae")
    sorted_performers = sorted(performers.keys(), key=len, reverse=True)
    
    while i < len(expr):
        c = expr[i]
        
        if c == '!':
            # Check for !@ (bare) = explicit none (admin said "no performers")
            if i + 1 < len(expr) and expr[i + 1] == '@':
                rest = expr[i + 2:]
                is_bare = True
                for name in sorted_performers:
                    if name != '_none' and rest.startswith(name):
                        is_bare = False
                        break
                if is_bare:
                    # !@ alone = EXPLICIT_NONE token
                    if tokens and (isinstance(tokens[-1], tuple) or tokens[-1] in (')', 'EXPLICIT_NONE', 'UNSET_PERFORMER')):
                        tokens.append('AND')
                    tokens.append('EXPLICIT_NONE')
                    i += 2  # skip !@
                    continue
            # Implicit AND before NOT if previous token is a value
            if tokens and (isinstance(tokens[-1], tuple) or tokens[-1] in (')', 'EXPLICIT_NONE', 'UNSET_PERFORMER')):
                tokens.append('AND')
            tokens.append('NOT')
            i += 1
        elif c == '?':
            # Check for ?@ = unset performers (not tagged yet)
            if i + 1 < len(expr) and expr[i + 1] == '@':
                # But only if NOT followed by a performer name (i.e. ?@ alone or ?@ at end)
                # If followed by a known performer name, fall through to normal UNSET+@performer
                rest = expr[i + 2:]
                is_bare = True
                for name in sorted_performers:
                    if name != '_none' and rest.startswith(name):
                        is_bare = False
                        break
                if is_bare:
                    # ?@ alone = UNSET_PERFORMER token
                    if tokens and (isinstance(tokens[-1], tuple) or tokens[-1] in (')', 'EXPLICIT_NONE', 'UNSET_PERFORMER')):
                        tokens.append('AND')
                    tokens.append('UNSET_PERFORMER')
                    i += 2  # skip ?@
                    continue
            # Implicit AND before UNSET if previous token is a value
            if tokens and (isinstance(tokens[-1], tuple) or tokens[-1] in (')', 'EXPLICIT_NONE', 'UNSET_PERFORMER')):
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
            # Implicit AND before ( if previous token is a value
            if tokens and (isinstance(tokens[-1], tuple) or tokens[-1] in (')', 'EXPLICIT_NONE', 'UNSET_PERFORMER')):
                tokens.append('AND')
            tokens.append('(')
            i += 1
        elif c == ')':
            tokens.append(')')
            i += 1
        elif c == '@':
            # Performer token: @Name
            # Implicit AND before @ if previous token is a value
            if tokens and (isinstance(tokens[-1], tuple) or tokens[-1] in (')', 'EXPLICIT_NONE', 'UNSET_PERFORMER')):
                tokens.append('AND')
            i += 1  # skip @
            found = False
            for name in sorted_performers:
                if expr[i:].startswith(name):
                    tokens.append(('PERFORMER', name))
                    i += len(name)
                    found = True
                    break
            if not found:
                raise ValueError(f"Unknown performer at position {i}: '@{expr[i:][:20]}'")
        else:
            # Look for an emoji
            found = False
            for emoji in sorted_emojis:
                if expr[i:].startswith(emoji):
                    # Implicit AND if previous token is a value
                    if tokens and (isinstance(tokens[-1], tuple) or tokens[-1] in (')', 'EXPLICIT_NONE', 'UNSET_PERFORMER')):
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
    
    def __init__(self, tokens: list, categories: dict, performers: dict = None):
        self.tokens = tokens
        self.pos = 0
        self.categories = categories
        self.performers = performers or {}
    
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
            token = self.peek()
            if isinstance(token, tuple) and token[0] == 'EMOJI':
                self.consume()
                emoji = token[1]
                return self.categories[emoji]["no"].copy()
            elif isinstance(token, tuple) and token[0] == 'PERFORMER':
                # !@performer = videos that do NOT have this performer
                self.consume()
                name = token[1]
                return ~self.performers[name].copy()
            else:
                # NOT of a sub-expression
                inner = self.parse_not()
                return ~inner
        
        if self.peek() == 'UNSET':
            self.consume('UNSET')
            token = self.peek()
            if isinstance(token, tuple) and token[0] == 'EMOJI':
                self.consume()
                emoji = token[1]
                yes = self.categories[emoji]["yes"]
                no = self.categories[emoji]["no"]
                return ~(yes | no)
            elif isinstance(token, tuple) and token[0] == 'PERFORMER':
                # ?@performer = videos where this performer status is unset
                # (semantically same result as !@performer since performers are binary)
                self.consume()
                name = token[1]
                return ~self.performers[name].copy()
            else:
                inner = self.parse_not()
                return ~inner
        
        return self.parse_atom()
    
    def parse_atom(self) -> bitarray:
        """atom → EMOJI | PERFORMER | EXPLICIT_NONE | UNSET_PERFORMER | '(' expr_or ')'"""
        token = self.peek()
        
        if token == '(':
            self.consume('(')
            result = self.parse_or()
            self.consume(')')
            return result
        
        if token == 'EXPLICIT_NONE':
            self.consume()
            # !@ = admin explicitly marked "no performers" → _none bitarray
            if "_none" in self.performers:
                return self.performers["_none"].copy()
            # Fallback: no _none performer → no videos match
            n = len(list(self.categories.values())[0]["yes"])
            result = bitarray(n)
            result.setall(0)
            return result

        if token == 'UNSET_PERFORMER':
            self.consume()
            # ?@ = unset performers (admin hasn't tagged yet)
            # = NOT(_none OR any_real_performer)
            n = len(list(self.categories.values())[0]["yes"])
            tagged = bitarray(n)
            tagged.setall(0)
            for name, bits in self.performers.items():
                tagged |= bits
            return ~tagged
        
        if isinstance(token, tuple) and token[0] == 'EMOJI':
            self.consume()
            emoji = token[1]
            return self.categories[emoji]["yes"].copy()
        
        if isinstance(token, tuple) and token[0] == 'PERFORMER':
            self.consume()
            name = token[1]
            return self.performers[name].copy()
        
        raise ValueError(f"Unexpected token: {token}")


def evaluate(expr: str, categories: dict, performers: dict = None) -> bitarray:
    """
    Evaluate a boolean expression on categories and performers.
    
    Syntax:
      !  = NOT (before emoji: looks in "no", before expr: inverts)
      +  = OR
      .  = AND (optional, concatenation = implicit AND)
      () = grouping
      @  = performer (e.g. @Sage_bd)
    
    Args:
        expr: Expression like "🥗.!👎" or "🔥+💃" or "@Sage_bd"
        categories: dict[emoji, {"yes": bitarray, "no": bitarray}]
        performers: dict[name, bitarray] (optional)
    
    Returns:
        bitarray with 1 for each matching video
    """
    if not categories:
        raise ValueError("No categories loaded")
    
    if not expr.strip():
        raise ValueError("Empty expression")
    
    tokens = tokenize(expr, categories, performers)
    parser = Parser(tokens, categories, performers)
    return parser.parse()
