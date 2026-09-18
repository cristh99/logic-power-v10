from __future__ import annotations
import copy,json,subprocess,tempfile,unittest
from pathlib import Path
from logic_power_knowledge_action_loop_v1.certificate import verify_certificate
from logic_power_knowledge_action_loop_v1.model import (
 ActionRecord,ActionState,ConsequenceRecord,EpistemicStatus,EvidenceRecord,
 KnowledgeRecord,LoopState,Preflight,Verdict,apply_knowledge_to_existing_action,
 complete_action,create_action_from_knowledge,integrate_action_evidence_as_knowledge,
 issue_solver_mandate,record_consequence,record_evidence,register_action,
 register_knowledge,start_action,verify_receipt_chain)
from logic_power_knowledge_action_loop_v1.run_demo import all_pass_preflight,build_demo
NOW="2026-08-03T18:00:00Z"
def knowledge(i="K1"):return KnowledgeRecord(i,"A verified fact.",EpistemicStatus.VERIFIED,("source",))
def action(i="A1",state=ActionState.SOMEDAY_MAYBE,**kw):
 d=dict(action_id=i,title="Do bounded work",state=state,result_contract="Produce a verified result",change_contract="Change only the declared surface",verification_contract="Independent evidence required")
 if state in {ActionState.ASAP,ActionState.AT_A_DATE,ActionState.DOING}:d["authorized_by"]="user"
 if state is ActionState.AT_A_DATE:d["scheduled_at"]="2026-08-03T19:00:00Z"
 if state is ActionState.DOING:d["last_activity_at"]=NOW
 d.update(kw);return ActionRecord(**d)
class Invariants(unittest.TestCase):
 def test_knowledge_requires_provenance(self):
  with self.assertRaises(ValueError):KnowledgeRecord("K","x",EpistemicStatus.CLAIMED,())
 def test_committed_requires_authorization(self):
  with self.assertRaises(ValueError):action(state=ActionState.ASAP,authorized_by=None)
 def test_at_date_requires_date(self):
  with self.assertRaises(ValueError):action(state=ActionState.AT_A_DATE,scheduled_at=None)
 def test_doing_requires_liveness(self):
  with self.assertRaises(ValueError):action(state=ActionState.DOING,last_activity_at=None)
 def test_done_requires_evidence(self):
  with self.assertRaises(ValueError):action(state=ActionState.DONE)
 def test_someday_cannot_claim_activity(self):
  with self.assertRaises(ValueError):action(last_activity_at=NOW)
 def test_knowledge_action_ids_disjoint(self):
  s=register_knowledge(LoopState(),knowledge("SAME"),occurred_at=NOW,rationale="fact")
  with self.assertRaises(ValueError):register_action(s,action("SAME"),occurred_at=NOW,rationale="work")
class KnowledgeToAction(unittest.TestCase):
 def setUp(self):
  s=register_knowledge(LoopState(),knowledge(),occurred_at=NOW,rationale="fact")
  self.s=register_action(s,action(),occurred_at=NOW,rationale="future")
 def test_no_change_cannot_mutate(self):
  with self.assertRaises(ValueError):ConsequenceRecord("C","K1",Verdict.NO_CHANGE,"none",action_id="A1")
 def test_create_requires_destination_search(self):
  with self.assertRaises(ValueError):ConsequenceRecord("C","K1",Verdict.CREATE,"new")
 def test_knowledge_cannot_claim_doing(self):
  with self.assertRaises(ValueError):ConsequenceRecord("C","K1",Verdict.MOVE,"start","A1",ActionState.DOING)
 def test_move_someday_to_asap(self):
  c=ConsequenceRecord("C","K1",Verdict.MOVE,"now feasible","A1",ActionState.ASAP)
  s=record_consequence(self.s,c,occurred_at=NOW);s=apply_knowledge_to_existing_action(s,"C",authorized_by="user",occurred_at="2026-08-03T18:01:00Z")
  self.assertEqual(s.get_action("A1").state,ActionState.ASAP);self.assertIn("K1",s.get_action("A1").related_knowledge_ids)
 def test_created_action_links_knowledge(self):
  c=ConsequenceRecord("C","K1",Verdict.CREATE,"none exists",existing_destination_checked=True);s=record_consequence(self.s,c,occurred_at=NOW)
  with self.assertRaises(ValueError):create_action_from_knowledge(s,"C",action("A2"),occurred_at=NOW)
  s=create_action_from_knowledge(s,"C",action("A2",related_knowledge_ids=("K1",)),occurred_at=NOW);self.assertEqual(s.get_action("A2").state,ActionState.SOMEDAY_MAYBE)
class Execution(unittest.TestCase):
 def setUp(self):self.s=register_action(LoopState(),action(state=ActionState.ASAP),occurred_at=NOW,rationale="ready")
 def test_someday_cannot_start(self):
  s=register_action(LoopState(),action(),occurred_at=NOW,rationale="future")
  with self.assertRaises(ValueError):start_action(s,"A1",all_pass_preflight(),occurred_at=NOW)
 def test_future_date_cannot_start(self):
  s=register_action(LoopState(),action(state=ActionState.AT_A_DATE),occurred_at=NOW,rationale="scheduled")
  with self.assertRaises(ValueError):start_action(s,"A1",all_pass_preflight(),occurred_at="2026-08-03T18:59:59Z")
 def test_failed_preflight_blocks(self):
  p=Preflight(True,True,True,True,True,True,False,True,True,True,True,True)
  with self.assertRaisesRegex(ValueError,"evaluator"):start_action(self.s,"A1",p,occurred_at=NOW)
 def test_verified_evidence_closes(self):
  s=start_action(self.s,"A1",all_pass_preflight(),occurred_at=NOW);e=EvidenceRecord("E1","A1","passed","a"*64,"independent",True,"2026-08-03T18:10:00Z","Reusable.")
  s=record_evidence(s,e);s=complete_action(s,"A1","E1",occurred_at="2026-08-03T18:11:00Z");self.assertEqual(s.get_action("A1").state,ActionState.DONE)
 def test_unverified_cannot_close(self):
  s=start_action(self.s,"A1",all_pass_preflight(),occurred_at=NOW);e=EvidenceRecord("E1","A1","uncertain","b"*64,"candidate",False,"2026-08-03T18:10:00Z")
  s=record_evidence(s,e)
  with self.assertRaises(ValueError):complete_action(s,"A1","E1",occurred_at="2026-08-03T18:11:00Z")
class ActionToKnowledge(unittest.TestCase):
 def completed(self,generalizable=True):
  s=register_action(LoopState(),action(state=ActionState.ASAP),occurred_at=NOW,rationale="work");s=start_action(s,"A1",all_pass_preflight(),occurred_at=NOW)
  e=EvidenceRecord("E1","A1","passed","c"*64,"independent",True,"2026-08-03T18:10:00Z","This result is reusable." if generalizable else None);s=record_evidence(s,e)
  return complete_action(s,"A1","E1",occurred_at="2026-08-03T18:11:00Z")
 def test_local_result_not_knowledge(self):
  s=self.completed(False);k=KnowledgeRecord("K1","This result is reusable.",EpistemicStatus.VERIFIED,("run",),("E1",))
  with self.assertRaises(ValueError):integrate_action_evidence_as_knowledge(s,"E1",k,occurred_at="2026-08-03T18:12:00Z")
 def test_generalizable_result_integrates(self):
  s=self.completed();k=KnowledgeRecord("K1","This result is reusable.",EpistemicStatus.VERIFIED,("run",),("E1",));s=integrate_action_evidence_as_knowledge(s,"E1",k,occurred_at="2026-08-03T18:12:00Z");self.assertEqual(s.get_knowledge("K1").statement,k.statement)
class Mandates(unittest.TestCase):
 def test_solver_cannot_create_authority(self):
  s=register_action(LoopState(),action(),occurred_at=NOW,rationale="future")
  with self.assertRaises(ValueError):issue_solver_mandate(s,"A1",occurred_at=NOW,constraints=(),knowledge_ids=(),capabilities=("logic_power_v10",),budget={"money_usd":"0"})
 def test_mandate_bound_to_state(self):
  s=register_knowledge(LoopState(),knowledge(),occurred_at=NOW,rationale="context");s=register_action(s,action(state=ActionState.ASAP,related_knowledge_ids=("K1",)),occurred_at=NOW,rationale="ready")
  m=issue_solver_mandate(s,"A1",occurred_at=NOW,constraints=("read only",),knowledge_ids=("K1",),capabilities=("logic_power_v10","wolfram"),budget={"money_usd":"0"});self.assertEqual(m.state_sha256,s.core_fingerprint())
class Certificates(unittest.TestCase):
 def test_demo_deterministic_and_valid(self):
  s1,c1=build_demo();s2,c2=build_demo();self.assertEqual(s1.canonical_data(),s2.canonical_data());self.assertEqual(c1,c2);self.assertEqual(verify_receipt_chain(s1),());self.assertEqual(verify_certificate(c1),())
 def test_tamper_rejected(self):
  _,c=build_demo();bad=copy.deepcopy(c);bad["payload"]["result"]["action_count"]=999;self.assertIn("payload-hash",verify_certificate(bad))
 def test_independent_node(self):
  _,c=build_demo();v=Path(__file__).with_name("verify_lp_kal_v1.js")
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/"c.json";p.write_text(json.dumps(c));r=subprocess.run(["node",str(v),str(p)],capture_output=True,text=True,check=False);self.assertEqual(r.returncode,0,r.stderr+r.stdout)
if __name__=="__main__":unittest.main()
