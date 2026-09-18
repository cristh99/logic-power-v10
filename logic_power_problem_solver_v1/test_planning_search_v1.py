from __future__ import annotations

import unittest
from fractions import Fraction

from logic_power_problem_solver_v1.mcts import plan_with_mcts
from logic_power_problem_solver_v1.planning import (
    MDPTransition,
    solve_finite_horizon_mdp,
)


STATES = ("root", "middle", "terminal")
ACTIONS = {
    "root": ("explore", "safe"),
    "middle": ("bad", "good"),
    "terminal": (),
}
TRANSITIONS = {
    ("root", "safe"): (
        MDPTransition("terminal", Fraction(1), Fraction(4)),
    ),
    ("root", "explore"): (
        MDPTransition("middle", Fraction(1), Fraction(0)),
    ),
    ("middle", "good"): (
        MDPTransition("terminal", Fraction(1), Fraction(10)),
    ),
    ("middle", "bad"): (
        MDPTransition("terminal", Fraction(1), Fraction(-10)),
    ),
}


def actions_for(state: str) -> tuple[str, ...]:
    return ACTIONS[state]


def deterministic_step(
    state: str,
    action: str,
) -> tuple[str, Fraction, bool]:
    transition = TRANSITIONS[(state, action)][0]
    next_state = transition.next_state
    return next_state, transition.reward, next_state == "terminal"


class FinitePlanningTests(unittest.TestCase):
    def test_exact_finite_horizon_planner_finds_optimal_policy(self):
        result = solve_finite_horizon_mdp(
            states=STATES,
            actions_by_state=ACTIONS,
            transitions=TRANSITIONS,
            terminal_states=("terminal",),
            start_state="root",
            horizon=2,
        )
        self.assertEqual(result.start_action, "explore")
        self.assertEqual(result.start_value, Fraction(10))
        self.assertEqual(result.policy["0:root"], "explore")
        self.assertEqual(result.policy["1:middle"], "good")

    def test_exact_planner_rejects_invalid_probability_mass(self):
        broken = dict(TRANSITIONS)
        broken[("root", "safe")] = (
            MDPTransition("terminal", Fraction(1, 2), Fraction(4)),
        )
        with self.assertRaises(ValueError):
            solve_finite_horizon_mdp(
                states=STATES,
                actions_by_state=ACTIONS,
                transitions=broken,
                terminal_states=("terminal",),
                start_state="root",
                horizon=2,
            )


class MCTSTests(unittest.TestCase):
    def test_seeded_mcts_is_deterministic(self):
        first = plan_with_mcts(
            start_state="root",
            actions=actions_for,
            step=deterministic_step,
            horizon=2,
            rollouts=500,
            seed=17,
        )
        second = plan_with_mcts(
            start_state="root",
            actions=actions_for,
            step=deterministic_step,
            horizon=2,
            rollouts=500,
            seed=17,
        )
        self.assertEqual(first, second)

    def test_mcts_matches_exact_root_action_under_fixed_budget(self):
        result = plan_with_mcts(
            start_state="root",
            actions=actions_for,
            step=deterministic_step,
            horizon=2,
            rollouts=500,
            seed=17,
        )
        self.assertEqual(result.action, "explore")
        self.assertGreater(
            result.action_visits["explore"],
            result.action_visits["safe"],
        )
        self.assertGreater(
            result.action_mean_returns["explore"],
            result.action_mean_returns["safe"],
        )

    def test_mcts_rejects_nondeterministic_simulator(self):
        calls: dict[tuple[str, str], int] = {}

        def unstable_step(
            state: str,
            action: str,
        ) -> tuple[str, Fraction, bool]:
            key = (state, action)
            calls[key] = calls.get(key, 0) + 1
            next_state, reward, terminal = deterministic_step(state, action)
            if calls[key] > 1:
                reward += Fraction(1)
            return next_state, reward, terminal

        with self.assertRaises(ValueError):
            plan_with_mcts(
                start_state="root",
                actions=actions_for,
                step=unstable_step,
                horizon=2,
                rollouts=50,
                seed=17,
            )


if __name__ == "__main__":
    unittest.main()
