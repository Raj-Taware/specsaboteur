// Intent: Find target in sorted array, return index or -1 if not found
// Known gap: missing not-found completeness (doesn't ensure target is absent when returning -1)

method BinarySearch(a: array<int>, target: int) returns (index: int)
  requires forall i :: 0 <= i < a.Length - 1 ==> a[i] <= a[i+1]
  ensures index >= 0 ==> 0 <= index < a.Length && a[index] == target
{
  // Implementation intentionally left empty for adversarial generation
}
