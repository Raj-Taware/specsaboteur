// Intent: Return the absolute value of an integer
// Known gap: missing ensures result >= 0

method Abs(x: int) returns (result: int)
  ensures x >= 0 ==> result == x
{
  // Implementation intentionally left empty for adversarial generation
}
