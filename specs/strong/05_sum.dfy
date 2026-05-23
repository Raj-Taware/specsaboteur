// Intent: Sum all elements of an integer array
// STRONG spec — uses ghost function for complete sum definition

function SumSeq(s: seq<int>): int
{
  if |s| == 0 then 0
  else s[0] + SumSeq(s[1..])
}

method Sum(a: array<int>) returns (s: int)
  ensures s == SumSeq(a[..])
{
  // Implementation intentionally left empty for adversarial generation
}
