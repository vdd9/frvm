/***********************
 * SwipeDetector
 ***********************/
class SwipeDetector {
  constructor({
    element,
    allowedDirections = ["left", "right", "up", "down"],
    minDistance = 40,
    angleTolerance = 22.5,
    resistance = 0.35,
    onMove = () => {},
    onDetect = () => {},
    onEnd = () => {},
    onCancel = () => {}
  }) {
    this.el = element;
    this.allowed = new Set(allowedDirections);

    this.minDistance = minDistance;
    this.angleTolerance = angleTolerance;
    this.resistance = resistance;

    this.onMove = onMove;
    this.onDetect = onDetect;
    this.onEnd = onEnd;
    this.onCancel = onCancel;

    this.active = false;
    this.lockedDirection = null;

    this.startX = 0;
    this.startY = 0;

    this.el.style.touchAction = "none";

    this._bind();
  }

  _bind() {
    this.el.addEventListener("pointerdown", this._down);
    this.el.addEventListener("pointermove", this._move);
    this.el.addEventListener("pointerup", this._up);
    this.el.addEventListener("pointercancel", this._cancel);
  }

  destroy() {
    this.el.removeEventListener("pointerdown", this._down);
    this.el.removeEventListener("pointermove", this._move);
    this.el.removeEventListener("pointerup", this._up);
    this.el.removeEventListener("pointercancel", this._cancel);
  }

  _down = e => {
    if (!e.isTrusted) return;

    this.active = true;
    this.lockedDirection = null;

    this.startX = e.clientX;
    this.startY = e.clientY;

    this.el.setPointerCapture(e.pointerId);
  };

  _move = e => {
    if (!this.active) return;

    const dxRaw = e.clientX - this.startX;
    const dyRaw = e.clientY - this.startY;

    const distance = Math.hypot(dxRaw, dyRaw);

    // Feedback continu avec inertie
    this.onMove({
      dx: dxRaw * this.resistance,
      dy: dyRaw * this.resistance,
      distance,
      event: e
    });

    if (this.lockedDirection || distance < this.minDistance) return;

    const direction = this._resolveDirection(dxRaw, dyRaw);
    if (!direction) return;

    this.lockedDirection = direction;

    // 🔥 Détection AVANT relâchement
    this.onDetect({
      direction,
      distance,
      dx: dxRaw,
      dy: dyRaw,
      event: e
    });
  };

  _up = e => {
    if (!this.active) return;

    this.active = false;
    this.el.releasePointerCapture(e.pointerId);

    if (this.lockedDirection) {
      this.onEnd({
        direction: this.lockedDirection,
        event: e
      });
    } else {
      this.onCancel();
    }
  };

  _cancel = () => {
    this.active = false;
    this.lockedDirection = null;
    this.onCancel();
  };

  /*************************
   * Détection angulaire
   *************************/
  _resolveDirection(dx, dy) {
    const angle = (Math.atan2(dy, dx) * 180 / Math.PI + 360) % 360;

    const directions = [
      { name: "right",      angle: 0   },
      { name: "down-right", angle: 45  },
      { name: "down",       angle: 90  },
      { name: "down-left",  angle: 135 },
      { name: "left",       angle: 180 },
      { name: "up-left",    angle: 225 },
      { name: "up",         angle: 270 },
      { name: "up-right",   angle: 315 }
    ];

    let best = null;
    let bestDelta = Infinity;

    for (const d of directions) {
      if (!this.allowed.has(d.name)) continue;

      const delta = Math.min(
        Math.abs(angle - d.angle),
        360 - Math.abs(angle - d.angle)
      );

      if (delta < bestDelta) {
        bestDelta = delta;
        best = d.name;
      }
    }

    if (bestDelta > this.angleTolerance) return null;
    return best;
  }
}
