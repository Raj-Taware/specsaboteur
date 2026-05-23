// Intent: Return the maximum element of a non-empty array
// Known gap: missing "greater than or equal to all elements" constraint

method Max(a: array<int>) returns (m: int)
  requires a.Length > 0
  ensures exists i :: 0 <= i < a.Length && a[i] == m
{
  // Implementation intentionally left empty for adversarial generation
}
