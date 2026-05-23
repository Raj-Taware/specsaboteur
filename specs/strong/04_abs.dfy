// Intent: Return the absolute value of an integer
// STRONG spec — both positive and negative cases explicit

method Abs(x: int) returns (result: int)
  ensures x >= 0 ==> result == x
  ensures x < 0 ==> result == -x
  ensures result >= 0
{
  // Implementation intentionally left empty for adversarial generation
}
