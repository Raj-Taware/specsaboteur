// Intent: Find the FIRST occurrence of a value in an array
// MEDIUM spec: found→correct + not-found→absent + index valid
// Known remaining gap: doesn't ensure it's the FIRST (minimum index) match
// (e.g., for [1,2,1] finding 1, could return index 2 instead of 0)

method FindFirst(a: array<int>, target: int) returns (index: int)
  ensures index >= -1 && index < a.Length
  ensures index >= 0 ==> a[index] == target
  ensures index == -1 ==> forall i :: 0 <= i < a.Length ==> a[i] != target
{
  // Implementation intentionally left empty for adversarial generation
}
