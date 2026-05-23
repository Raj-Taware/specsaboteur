// Intent: Sum all elements of an integer array
// MEDIUM spec: empty array → 0, single element → that element
// Known remaining gap: no general sum definition for arrays with 2+ elements
// (e.g., for [3,5,7] could return 3+5=8 ignoring last element)

method Sum(a: array<int>) returns (s: int)
  ensures a.Length == 0 ==> s == 0
  ensures a.Length == 1 ==> s == a[0]
{
  // Implementation intentionally left empty for adversarial generation
}
