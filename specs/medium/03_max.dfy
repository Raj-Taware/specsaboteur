// Intent: Return the maximum element of a non-empty array
// MEDIUM spec: result >= all elements (upper bound)
// Known remaining gap: doesn't require result is actually IN the array
// (e.g., returning INT_MAX satisfies "forall a[i] <= m" but isn't an element)

method Max(a: array<int>) returns (m: int)
  requires a.Length > 0
  ensures forall i :: 0 <= i < a.Length ==> a[i] <= m
{
  // Implementation intentionally left empty for adversarial generation
}
