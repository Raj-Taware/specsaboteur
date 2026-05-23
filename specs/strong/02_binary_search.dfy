// Intent: Find target in sorted array, return index or -1 if not found
// STRONG spec — found→correct, not-found→absent, must-find if exists

method BinarySearch(a: array<int>, target: int) returns (index: int)
  requires forall i :: 0 <= i < a.Length - 1 ==> a[i] <= a[i+1]
  ensures index >= 0 ==> 0 <= index < a.Length && a[index] == target
  ensures index < 0 ==> forall i :: 0 <= i < a.Length ==> a[i] != target
  ensures (exists i :: 0 <= i < a.Length && a[i] == target) ==> index >= 0
{
  // Implementation intentionally left empty for adversarial generation
}
