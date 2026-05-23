// Intent: Return the maximum element of a non-empty array
// STRONG spec - includes both existence and upper bound

method Max(a: array<int>) returns (m: int)
  requires a.Length > 0
  ensures exists i :: 0 <= i < a.Length && a[i] == m
  ensures forall i :: 0 <= i < a.Length ==> a[i] <= m
{
  // Implementation intentionally left empty for adversarial generation
}
