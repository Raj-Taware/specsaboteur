// Intent: Find the first occurrence of a value in an array
// Known gap: missing "first" constraint - could return any matching index

method FindFirst(a: array<int>, target: int) returns (index: int)
  ensures index >= 0 ==> 0 <= index < a.Length && a[index] == target
  ensures index < 0 ==> forall i :: 0 <= i < a.Length ==> a[i] != target
{
  // Implementation intentionally left empty for adversarial generation
}
