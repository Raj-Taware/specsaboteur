// Intent: Sort an array of integers in ascending order, preserving all elements
// MEDIUM spec: sorted + every output element existed in input
// Known remaining gap: doesn't prevent DUPLICATING elements from input
// (e.g., [3,1,2] -> [1,1,2] is sorted, all elements were in original, but 3 is lost)

method Sort(a: array<int>)
  modifies a
  ensures forall i :: 0 <= i < a.Length - 1 ==> a[i] <= a[i+1]
  ensures forall i :: 0 <= i < a.Length ==> a[i] in multiset(old(a[..]))
{
  // Implementation intentionally left empty for adversarial generation
}
