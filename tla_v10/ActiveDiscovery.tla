---- MODULE ActiveDiscovery ----
EXTENDS FiniteSets, TLC

CONSTANT Mode
VARIABLES belief, status, experiment

vars == <<belief, status, experiment>>
Hypotheses == {"h0", "h1"}
Statuses == {"Unknown", "True", "False", "Impossible"}
Experiments == IF Mode = "Exact" THEN {"sep"} ELSE {"flat"}

Property(h) == h = "h1"
Observation(e, h) == IF e = "sep" THEN h ELSE "same"
Conflict(B) == \E a, b \in B : Property(a) # Property(b)
Indistinguishable(B) ==
  \E a, b \in B :
    /\ Property(a) # Property(b)
    /\ \A e \in Experiments :
         Observation(e, a) = Observation(e, b)

Init ==
  /\ belief = Hypotheses
  /\ status = "Unknown"
  /\ experiment = "None"

ExactStep ==
  /\ Mode = "Exact"
  /\ status = "Unknown"
  /\ experiment' = "sep"
  /\ \/ /\ belief' = {"h0"}
         /\ status' = "False"
     \/ /\ belief' = {"h1"}
         /\ status' = "True"

ImpossibleStep ==
  /\ Mode = "Impossible"
  /\ status = "Unknown"
  /\ experiment' = "flat"
  /\ belief' = belief
  /\ status' = "Impossible"

TerminalStep ==
  /\ status # "Unknown"
  /\ UNCHANGED vars

Next == ExactStep \/ ImpossibleStep \/ TerminalStep
ActiveStep == ExactStep \/ ImpossibleStep
Spec == Init /\ [][Next]_vars /\ WF_vars(ActiveStep)

TypeOK ==
  /\ Mode \in {"Exact", "Impossible"}
  /\ belief \subseteq Hypotheses
  /\ status \in Statuses
  /\ experiment \in Experiments \union {"None"}

BeliefNonempty == belief # {}
TrueSound ==
  status = "True" => \A h \in belief : Property(h)
FalseSound ==
  status = "False" => \A h \in belief : ~Property(h)
ImpossibleSound ==
  status = "Impossible" =>
    Mode = "Impossible" /\ Indistinguishable(belief)
TerminalLegitimate ==
  status # "Unknown" =>
    status \in {"True", "False", "Impossible"}
Termination == <> (status # "Unknown")

====
