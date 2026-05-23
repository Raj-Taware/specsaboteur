// Intent: Sort an array of integers in ascending order, preserving all elements
// STRONG spec - includes permutation property

method Sort(a: array<int>)
  modifies a
  ensures forall i :: 0 <= i < a.Length - 1 ==> a[i] <= a[i+1]
  ensures multiset(a[..]) == multiset(old(a[..]))
{
  // Implementation intentionally left empty for adversarial generation
}
