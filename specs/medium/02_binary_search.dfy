// Intent: Find target in sorted array, return index or -1 if not found
// MEDIUM spec: found→correct + not-found→absent
// Known remaining gap: doesn't ensure it MUST find target if it exists
// (e.g., always returning -1 satisfies both ensures vacuously/correctly for "not found")

method BinarySearch(a: array<int>, target: int) returns (index: int)
  requires forall i :: 0 <= i < a.Length - 1 ==> a[i] <= a[i+1]
  ensures index >= 0 ==> 0 <= index < a.Length && a[index] == target
  ensures index < 0 ==> forall i :: 0 <= i < a.Length ==> a[i] != target
{
  // Implementation intentionally left empty for adversarial generation
}
