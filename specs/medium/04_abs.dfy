// Intent: Return the absolute value of an integer
// MEDIUM spec: positive case correct + result non-negative
// Known remaining gap: doesn't specify what happens for negative input
// (e.g., Abs(-5) could return 0 or 42 — satisfies result >= 0 and x >= 0 ==> result == x)

method Abs(x: int) returns (result: int)
  ensures x >= 0 ==> result == x
  ensures result >= 0
{
  // Implementation intentionally left empty for adversarial generation
}
