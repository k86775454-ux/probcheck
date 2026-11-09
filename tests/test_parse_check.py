"""Parser and deterministic checker: the cases from Lab 3 Tests A and B, plus edge cases."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import checker, parse

EXPECTED_SECTION = {"def_exclusive": "2.1", "def_independent": "2.3", "excl_pos_not_indep": "2.3",
                    "excl_zero_indep": "2.3", "addition_general": "2.2", "addition_exclusive": "2.1",
                    "conditional_def": "2.4", "bounds": "2.2"}


class ParseTests(unittest.TestCase):
    def test_lab3_test_b_referent_is_unclear(self):
        i = parse.parse("Are they independent? I don't have the numbers.")
        self.assertFalse(i["referent_clear"])
        self.assertEqual({}, i["values"])

    def test_values_and_notation(self):
        i = parse.parse("P(A and B) = 1/10, P(B)=40%. What is P(A|B)?")
        self.assertEqual("conditional", i["question_type"])
        self.assertEqual({"P(A∩B)": 0.1, "P(B)": 0.4}, i["values"])

    def test_impossible_values_are_problems(self):
        self.assertTrue(parse.parse("P(A)=1.4, P(B)=0.2. Are A and B independent?")["problems"])
        self.assertTrue(parse.parse("P(A)=0.2, P(B)=0.3, P(A∩B)=0.25. Independent?")["problems"])

    def test_correction_form_replaces_inference(self):
        i = parse.from_fields({"question_type": "independence",
                               "values": {"P(A)": "0.3", "P(B)": "0.5", "P(A∩B)": "0.15"}})
        self.assertTrue(i["corrected"] and i["referent_clear"])
        self.assertEqual("independent", checker.check(i)["verdict"])


class CheckerTests(unittest.TestCase):
    def test_lab3_test_a(self):
        r = checker.check(parse.parse("Can two events be mutually exclusive and independent? "
                                      "Let P(A)=0.4 and P(B)=0.5."))
        self.assertEqual(("checked", "not independent"), (r["status"], r["verdict"]))
        self.assertIn("0.4 × 0.5 = 0.2", " ".join(r["steps"]))

    def test_zero_probability_case(self):
        r = checker.check(parse.parse("Mutually exclusive and independent? P(A)=0, P(B)=0.5"))
        self.assertEqual("independent", r["verdict"])

    def test_general_question_depends_on_probabilities(self):
        r = checker.check(parse.parse("Can two events be mutually exclusive and independent?"))
        self.assertEqual("depends", r["status"])
        self.assertEqual(["P(A)", "P(B)"], r["needs"])

    def test_independence_numbers(self):
        r = checker.check(parse.parse("P(A)=0.3, P(B)=0.5, P(A∩B)=0.15. Are A and B independent?"))
        self.assertEqual("independent", r["verdict"])
        r = checker.check(parse.parse("P(A)=0.3, P(B)=0.5, P(A∩B)=0.2. Are A and B independent?"))
        self.assertEqual("not independent", r["verdict"])

    def test_conditional_undefined_when_pb_zero(self):
        r = checker.check(parse.parse("P(A∩B)=0, P(B)=0. What is P(A|B)?"))
        self.assertEqual("undefined", r["verdict"])

    def test_out_of_scope(self):
        self.assertEqual("cannot_check", checker.check(parse.parse("What is a Markov chain?"))["status"])

    def test_each_rule_resolves_to_its_own_section(self):
        for rule, section in EXPECTED_SECTION.items():
            hit = checker.find_support(rule)
            self.assertIsNotNone(hit, rule)
            self.assertTrue(hit["section"].startswith(section), (rule, hit["section"]))


if __name__ == "__main__":
    unittest.main()
