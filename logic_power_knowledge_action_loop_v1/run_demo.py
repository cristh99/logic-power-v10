"""Deterministic LP-KAL v1 demonstration."""
from __future__ import annotations
import json
from pathlib import Path
from .certificate import build_certificate
from .model import (
    ActionRecord,ActionState,ConsequenceRecord,EpistemicStatus,EvidenceRecord,
    KnowledgeRecord,LoopState,Preflight,Verdict,
    apply_knowledge_to_existing_action,complete_action,
    integrate_action_evidence_as_knowledge,issue_solver_mandate,
    record_consequence,record_evidence,register_action,register_knowledge,start_action,
)

def all_pass_preflight():
    return Preflight(True,True,True,True,True,True,True,True,True,True,True,True)

def build_demo():
    s=LoopState()
    finding=KnowledgeRecord("K_PORTAL_ROUTE","The public API route is cheaper than page-by-page navigation.",EpistemicStatus.VERIFIED,("official-api-canary",))
    s=register_knowledge(s,finding,occurred_at="2026-08-03T18:40:00Z",rationale="verified canary belongs in Knowledge")
    action=ActionRecord("A_ACQUIRE_SAMPLE","Acquire a verified public sample",ActionState.SOMEDAY_MAYBE,"Preserve 20 valid public files with hashes","Only public read routes; no bypass or destructive write","Magic bytes, SHA-256, provenance, and independent replay")
    s=register_action(s,action,occurred_at="2026-08-03T18:41:00Z",rationale="possible future work without current commitment")
    c=ConsequenceRecord("C_ROUTE_UNLOCKS_SAMPLE",finding.knowledge_id,Verdict.MOVE,"The verified route makes the bounded canary executable now.",action.action_id,ActionState.ASAP)
    s=record_consequence(s,c,occurred_at="2026-08-03T18:42:00Z")
    s=apply_knowledge_to_existing_action(s,c.consequence_id,authorized_by="user",occurred_at="2026-08-03T18:43:00Z")
    mandate=issue_solver_mandate(s,action.action_id,occurred_at="2026-08-03T18:44:00Z",constraints=("public routes only","zero destructive writes"),knowledge_ids=(finding.knowledge_id,),capabilities=("logic_power_v10","http_reader","sha256_verifier"),budget={"requests":"60","money_usd":"0","files":"20"})
    s=start_action(s,action.action_id,all_pass_preflight(),occurred_at="2026-08-03T18:45:00Z")
    evidence=EvidenceRecord("E_SAMPLE_PASS",action.action_id,"20 of 20 files passed byte, hash, and provenance checks.","a"*64,"independent-python-verifier",True,"2026-08-03T18:50:00Z","For the sealed canary, the public API route returned 20 of 20 valid files with reproducible hashes.")
    s=record_evidence(s,evidence)
    s=complete_action(s,action.action_id,evidence.evidence_id,occurred_at="2026-08-03T18:51:00Z")
    learned=KnowledgeRecord("K_CANARY_RESULT",evidence.generalizable_statement,EpistemicStatus.VERIFIED,("sealed-canary",),(evidence.evidence_id,))
    s=integrate_action_evidence_as_knowledge(s,evidence.evidence_id,learned,occurred_at="2026-08-03T18:52:00Z")
    no_change=ConsequenceRecord("C_NO_NEW_ACTION",learned.knowledge_id,Verdict.NO_CHANGE,"The result sharpens the existing program; no competing action is needed.")
    s=record_consequence(s,no_change,occurred_at="2026-08-03T18:53:00Z")
    result={"final_action_state":s.get_action(action.action_id).state.value,"knowledge_count":len(s.knowledge),"action_count":len(s.actions),"evidence_count":len(s.evidence),"consequence_count":len(s.consequences),"receipt_count":len(s.receipts),"solver_mandate_sha256":mandate.fingerprint(),"separation_preserved":not({x.knowledge_id for x in s.knowledge}&{x.action_id for x in s.actions}),"no_duplicate_action_created":len(s.actions)==1}
    return s,build_certificate(state=s,status="PASS",result=result,mandates=(mandate,))

def main():
    s,c=build_demo(); Path("reports").mkdir(exist_ok=True); Path("certificates").mkdir(exist_ok=True)
    Path("reports/lp_kal_v1_state.json").write_text(json.dumps(s.canonical_data(),indent=2,sort_keys=True)+"\n")
    Path("certificates/lp_kal_v1_demo.json").write_text(json.dumps(c,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"status":c["payload"]["status"],"state_sha256":c["payload"]["state_sha256"],"receipts":c["payload"]["receipt_count"]},sort_keys=True)); return 0
if __name__=="__main__":raise SystemExit(main())
