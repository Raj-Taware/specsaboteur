// Intent: Find the FIRST occurrence of a value in an array
// STRONG spec — found→correct, not-found→absent, FIRST (no earlier match)

method FindFirst(a: array<int>, target: int) returns (index: int)
  ensures index >= 0 ==> 0 <= index < a.Length && a[index] == target
  ensures index >= 0 ==> forall j :: 0 <= j < index ==> a[j] != target
  ensures index < 0 ==> forall i :: 0 <= i < a.Length ==> a[i] != target
{
  // Implementation intentionally left empty for adversarial generation
}
