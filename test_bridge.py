#!/usr/bin/env python3
"""Quick test of Dafny bridge — no LLM needed."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.dafny_bridge import DafnyBridge, extract_spec_from_file

# Need dafny on PATH
os.environ["PATH"] = os.path.expanduser("~/.dotnet/tools") + os.pathsep + os.environ["PATH"]

print("=== Testing DafnyBridge ===\n")

bridge = DafnyBridge()

# Test 1: Adversarial sort should VERIFY against weak spec
print("Test 1: Adversarial sort vs WEAK spec (should VERIFY)")
adv_sort = """
method Sort(a: array<int>)
  modifies a
  ensures forall i :: 0 <= i < a.Length - 1 ==> a[i] <= a[i+1]
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
"""
result = bridge.verify(adv_sort)
print(f"  Verified: {result.success}")
assert result.success, f"Expected verification to PASS! Errors: {result.errors}"
print("  PASS — adversarial impl verified (spec gap confirmed!)\n")

# Test 2: Same adversarial impl should FAIL against strong spec
print("Test 2: Adversarial sort vs STRONG spec (should FAIL)")
adv_sort_strong = """
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
"""
result = bridge.verify(adv_sort_strong)
print(f"  Verified: {result.success}")
assert not result.success, "Expected verification to FAIL!"
print("  PASS — strong spec rejected adversarial impl!\n")

# Test 3: Adversarial max (return first element)
print("Test 3: Adversarial Max vs weak spec")
adv_max = """
method Max(a: array<int>) returns (m: int)
  requires a.Length > 0
  ensures exists i :: 0 <= i < a.Length && a[i] == m
{
  m := a[0];  // Just return first element, not max
}
"""
result = bridge.verify(adv_max)
print(f"  Verified: {result.success}")
assert result.success, f"Expected verification to PASS! Errors: {result.errors}"
print("  PASS — returning first element satisfies weak spec (gap!)\n")

# Test 4: Adversarial binary search (always return -1)
print("Test 4: Adversarial BinarySearch vs weak spec")
adv_search = """
method BinarySearch(a: array<int>, target: int) returns (index: int)
  requires forall i :: 0 <= i < a.Length - 1 ==> a[i] <= a[i+1]
  ensures index >= 0 ==> 0 <= index < a.Length && a[index] == target
{
  index := -1;  // Always say "not found"
}
"""
result = bridge.verify(adv_search)
print(f"  Verified: {result.success}")
assert result.success, f"Expected verification to PASS! Errors: {result.errors}"
print("  PASS — always returning -1 satisfies weak spec (gap!)\n")

# Test 5: Extract spec from file
print("Test 5: Extract spec from file")
spec_info = extract_spec_from_file("specs/weak/01_sort.dfy")
print(f"  Intent: {spec_info['intent']}")
print(f"  Known gap: {spec_info['known_gap']}")
assert spec_info['intent'], "Should extract intent"
print("  PASS\n")

print("=" * 50)
print("ALL TESTS PASSED — DafnyBridge working correctly!")
print("=" * 50)
