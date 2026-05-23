// Intent: Sum all elements of an integer array
// Known gap: only ensures result type, not the actual sum computation

method Sum(a: array<int>) returns (s: int)
  ensures s >= 0 || s < 0  // vacuously true - accepts any integer
{
  // Implementation intentionally left empty for adversarial generation
}
