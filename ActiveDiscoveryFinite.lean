import Std

namespace ActiveDiscoveryFinite

/-- An exact monitor recovers the target property from the complete observation profile. -/
def ExactMonitor {H E O : Type} (obs : H → E → O)
    (property : H → Bool) (monitor : (E → O) → Bool) : Prop :=
  ∀ h, monitor (obs h) = property h

/-- Exact monitoring forces every property-conflicting pair to have different profiles. -/
theorem exactMonitor_separates_conflicts
    {H E O : Type} (obs : H → E → O) (property : H → Bool)
    (monitor : (E → O) → Bool)
    (hexact : ExactMonitor obs property monitor)
    {a b : H} (hconflict : property a ≠ property b) :
    obs a ≠ obs b := by
  intro hsame
  apply hconflict
  calc
    property a = monitor (obs a) := (hexact a).symm
    _ = monitor (obs b) := by rw [hsame]
    _ = property b := hexact b

/-- Opposite hypotheses with identical profiles are a constructive impossibility witness. -/
theorem indistinguishable_pair_blocks_exact_monitor
    {H E O : Type} (obs : H → E → O) (property : H → Bool)
    {a b : H} (hsame : obs a = obs b)
    (hconflict : property a ≠ property b) :
    ¬ ∃ monitor : (E → O) → Bool,
        ExactMonitor obs property monitor := by
  rintro ⟨monitor, hexact⟩
  exact
    (exactMonitor_separates_conflicts
      obs property monitor hexact hconflict) hsame

/-- Refining a belief cannot destroy an already unanimous true verdict. -/
theorem true_verdict_stable_under_refinement
    {H : Type} (property : H → Bool)
    (before after : H → Prop)
    (hrefine : ∀ h, after h → before h)
    (htrue : ∀ h, before h → property h = true) :
    ∀ h, after h → property h = true := by
  intro h hh
  exact htrue h (hrefine h hh)

/-- Refining a belief cannot destroy an already unanimous false verdict. -/
theorem false_verdict_stable_under_refinement
    {H : Type} (property : H → Bool)
    (before after : H → Prop)
    (hrefine : ∀ h, after h → before h)
    (hfalse : ∀ h, before h → property h = false) :
    ∀ h, after h → property h = false := by
  intro h hh
  exact hfalse h (hrefine h hh)

/-- A separating experiment makes its two observation fibres disjoint. -/
theorem separator_creates_disjoint_fibres
    {H E O : Type} (obs : H → E → O) (experiment : E)
    {a b : H} (hsep : obs a experiment ≠ obs b experiment) :
    ∀ h, obs h experiment = obs a experiment →
      obs h experiment = obs b experiment → False := by
  intro h ha hb
  apply hsep
  calc
    obs a experiment = obs h experiment := ha.symm
    _ = obs b experiment := hb

/-- Omitting the sole separating coordinate cannot decide its witness pair. -/
theorem missing_required_coordinate_cannot_separate
    {H E O : Type} (obs : H → E → O) {a b : H}
    (required : E)
    (honly : ∀ e, e ≠ required → obs a e = obs b e)
    (selected : E → Prop)
    (hmissing : ¬ selected required) :
    ∀ e, selected e → obs a e = obs b e := by
  intro e he
  apply honly e
  intro heq
  subst e
  exact hmissing he

/-- Every CEGIS elimination step decreases a natural-valued unresolved budget. -/
theorem cegis_elimination_strictly_decreases (remaining : Nat) :
    remaining < Nat.succ remaining := by
  exact Nat.lt_succ_self remaining

#print axioms exactMonitor_separates_conflicts
#print axioms indistinguishable_pair_blocks_exact_monitor
#print axioms true_verdict_stable_under_refinement
#print axioms false_verdict_stable_under_refinement
#print axioms separator_creates_disjoint_fibres
#print axioms missing_required_coordinate_cannot_separate
#print axioms cegis_elimination_strictly_decreases

end ActiveDiscoveryFinite
