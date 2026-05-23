// Same adversarial impl against STRONG spec (with multiset)
// Should FAIL verification — strong spec catches the attack

method Sort(a: array<int>)
  modifies a
  ensures forall i :: 0 <= i < a.Length - 1 ==> a[i] <= a[i+1]
  ensures multiset(a[..]) == multiset(old(a[..]))
{
  var i := 0;
  while i < a.Length
    invariant 0 <= i <= a.Length
    invariant forall j :: 0 <= j < i ==> a[j] == j
    invariant forall j :: 0 <= j < i - 1 ==> a[j] <= a[j+1]
  {
    a[i] := i;
    i := i + 1;
  }
}
