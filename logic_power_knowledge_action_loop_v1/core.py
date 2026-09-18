"""LP-KAL v1: typed, proof-carrying Knowledge ↔ Actions governance."""
from __future__ import annotations
import hashlib, json
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any, Iterable

STATE_SCHEMA="logic-power-knowledge-action-loop/state/1"
RECEIPT_SCHEMA="logic-power-knowledge-action-loop/receipt/1"
MANDATE_SCHEMA="logic-power-knowledge-action-loop/solver-mandate/1"
MAX_SAFE=2**53-1

class ActionState(str,Enum):
    ASAP="ASAP"; AT_A_DATE="AT_A_DATE"; DOING="DOING"; DONE="DONE"
    SOMEDAY_MAYBE="SOMEDAY_MAYBE"; TRASH="TRASH"
class Verdict(str,Enum):
    KILL="MATAR"; CHANGE="CAMBIAR"; MOVE="MOVER"; MERGE="FUSIONAR"
    CREATE="CREAR"; NO_CHANGE="SIN_CAMBIO"
class EpistemicStatus(str,Enum):
    CLAIMED="CLAIMED"; VERIFIED="VERIFIED"; REFUTED="REFUTED"
    LIMITED="LIMITED"; CONTRADICTED="CONTRADICTED"; UNKNOWN="UNKNOWN"

def text(n:str,v:str)->str:
    if not isinstance(v,str) or not v.strip(): raise ValueError(f"{n} must be non-empty")
    return v.strip()
def ident(n:str,v:str)->str:
    v=text(n,v)
    if any(c.isspace() for c in v): raise ValueError(f"{n} cannot contain whitespace")
    return v
def seq(n:str,vs:Iterable[str],ids:bool=True)->tuple[str,...]:
    out=tuple(sorted((ident if ids else text)(n,v) for v in vs))
    if len(out)!=len(set(out)): raise ValueError(f"duplicate {n}")
    return out
def utc(n:str,v:str|None)->str|None:
    if v is None:return None
    v=text(n,v)
    if len(v)!=20 or v[4]!="-" or v[7]!="-" or v[10]!="T" or v[-1]!="Z":
        raise ValueError(f"{n} must be UTC ISO-8601")
    return v
def norm(v:Any)->Any:
    if isinstance(v,Enum): return v.value
    if isinstance(v,dict):
        if any(not isinstance(k,str) for k in v): raise TypeError("non-string key")
        return {k:norm(v[k]) for k in sorted(v)}
    if isinstance(v,(tuple,list)): return [norm(x) for x in v]
    if isinstance(v,(str,bool)) or v is None:return v
    if isinstance(v,int):
        if abs(v)>MAX_SAFE: raise ValueError("unsafe integer")
        return v
    if isinstance(v,float): raise TypeError("floats forbidden")
    raise TypeError(f"unsupported type {type(v).__name__}")
def canonical(v:Any)->str:
    return json.dumps(norm(v),sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)
def fingerprint(v:Any)->str:return hashlib.sha256(canonical(v).encode()).hexdigest()
canonical_json=canonical
def hash_ok(v:Any)->bool:return isinstance(v,str) and len(v)==64 and all(c in "0123456789abcdef" for c in v)

@dataclass(frozen=True)
class KnowledgeRecord:
    knowledge_id:str; statement:str; status:EpistemicStatus; provenance:tuple[str,...]
    evidence_ids:tuple[str,...]=(); version:int=1
    def __post_init__(self):
        object.__setattr__(self,"knowledge_id",ident("knowledge_id",self.knowledge_id))
        object.__setattr__(self,"statement",text("statement",self.statement))
        if not isinstance(self.status,EpistemicStatus):raise TypeError("status")
        object.__setattr__(self,"provenance",seq("provenance",self.provenance,False))
        object.__setattr__(self,"evidence_ids",seq("evidence_ids",self.evidence_ids))
        if not self.provenance:raise ValueError("provenance required")
        if isinstance(self.version,bool) or not isinstance(self.version,int) or self.version<1:raise ValueError("version")
    def data(self):return {"knowledge_id":self.knowledge_id,"statement":self.statement,"status":self.status.value,"provenance":list(self.provenance),"evidence_ids":list(self.evidence_ids),"version":self.version}
    canonical_data=data

@dataclass(frozen=True)
class ActionRecord:
    action_id:str; title:str; state:ActionState; result_contract:str
    change_contract:str; verification_contract:str; authorized_by:str|None=None
    scheduled_at:str|None=None; last_activity_at:str|None=None
    evidence_ids:tuple[str,...]=(); related_knowledge_ids:tuple[str,...]=(); version:int=1
    def __post_init__(self):
        object.__setattr__(self,"action_id",ident("action_id",self.action_id))
        object.__setattr__(self,"title",text("title",self.title))
        if not isinstance(self.state,ActionState):raise TypeError("state")
        for n in ("result_contract","change_contract","verification_contract"):
            object.__setattr__(self,n,text(n,getattr(self,n)))
        if self.authorized_by is not None:object.__setattr__(self,"authorized_by",text("authorized_by",self.authorized_by))
        object.__setattr__(self,"scheduled_at",utc("scheduled_at",self.scheduled_at))
        object.__setattr__(self,"last_activity_at",utc("last_activity_at",self.last_activity_at))
        object.__setattr__(self,"evidence_ids",seq("evidence_ids",self.evidence_ids))
        object.__setattr__(self,"related_knowledge_ids",seq("related_knowledge_ids",self.related_knowledge_ids))
        if isinstance(self.version,bool) or not isinstance(self.version,int) or self.version<1:raise ValueError("version")
        if self.state in {ActionState.ASAP,ActionState.AT_A_DATE,ActionState.DOING} and self.authorized_by is None:raise ValueError("authorization required")
        if self.state is ActionState.AT_A_DATE and self.scheduled_at is None:raise ValueError("scheduled_at required")
        if self.state is ActionState.DOING and self.last_activity_at is None:raise ValueError("liveness required")
        if self.state is ActionState.DONE and not self.evidence_ids:raise ValueError("closure evidence required")
        if self.state in {ActionState.SOMEDAY_MAYBE,ActionState.TRASH} and self.last_activity_at is not None:raise ValueError("non-actionable cannot be live")
    def data(self):return {"action_id":self.action_id,"title":self.title,"state":self.state.value,"result_contract":self.result_contract,"change_contract":self.change_contract,"verification_contract":self.verification_contract,"authorized_by":self.authorized_by,"scheduled_at":self.scheduled_at,"last_activity_at":self.last_activity_at,"evidence_ids":list(self.evidence_ids),"related_knowledge_ids":list(self.related_knowledge_ids),"version":self.version}
    canonical_data=data

@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id:str; action_id:str; observation:str; artifact_sha256:str
    verifier:str; verified:bool; occurred_at:str; generalizable_statement:str|None=None
    def __post_init__(self):
        object.__setattr__(self,"evidence_id",ident("evidence_id",self.evidence_id)); object.__setattr__(self,"action_id",ident("action_id",self.action_id))
        object.__setattr__(self,"observation",text("observation",self.observation)); object.__setattr__(self,"verifier",text("verifier",self.verifier))
        if not hash_ok(self.artifact_sha256):raise ValueError("artifact_sha256")
        if not isinstance(self.verified,bool):raise TypeError("verified")
        object.__setattr__(self,"occurred_at",utc("occurred_at",self.occurred_at))
        if self.generalizable_statement is not None:object.__setattr__(self,"generalizable_statement",text("generalizable_statement",self.generalizable_statement))
    def data(self):return {"evidence_id":self.evidence_id,"action_id":self.action_id,"observation":self.observation,"artifact_sha256":self.artifact_sha256,"verifier":self.verifier,"verified":self.verified,"occurred_at":self.occurred_at,"generalizable_statement":self.generalizable_statement}
    canonical_data=data

@dataclass(frozen=True)
class ConsequenceRecord:
    consequence_id:str; knowledge_id:str; verdict:Verdict; rationale:str
    action_id:str|None=None; target_state:ActionState|None=None; existing_destination_checked:bool=False
    def __post_init__(self):
        object.__setattr__(self,"consequence_id",ident("consequence_id",self.consequence_id)); object.__setattr__(self,"knowledge_id",ident("knowledge_id",self.knowledge_id))
        if not isinstance(self.verdict,Verdict):raise TypeError("verdict")
        object.__setattr__(self,"rationale",text("rationale",self.rationale))
        if self.action_id is not None:object.__setattr__(self,"action_id",ident("action_id",self.action_id))
        if self.target_state is not None and not isinstance(self.target_state,ActionState):raise TypeError("target_state")
        if self.verdict is Verdict.NO_CHANGE and (self.action_id is not None or self.target_state is not None):raise ValueError("SIN_CAMBIO cannot mutate")
        if self.verdict is Verdict.CREATE and (not self.existing_destination_checked or self.action_id is not None):raise ValueError("CREAR requires destination search and no existing target")
        if self.verdict not in {Verdict.NO_CHANGE,Verdict.CREATE} and self.action_id is None:raise ValueError("existing action required")
        if self.target_state in {ActionState.DOING,ActionState.DONE}:raise ValueError("knowledge cannot claim execution")
    def data(self):return {"consequence_id":self.consequence_id,"knowledge_id":self.knowledge_id,"verdict":self.verdict.value,"rationale":self.rationale,"action_id":self.action_id,"target_state":self.target_state.value if self.target_state else None,"existing_destination_checked":self.existing_destination_checked}
    canonical_data=data

@dataclass(frozen=True)
class Preflight:
    authority:bool; current_state:bool; no_duplicate:bool; boundary:bool
    source_of_truth:bool; baseline:bool; evaluator:bool; reversible:bool
    permissions:bool; cost_limit:bool; review_capacity:bool; stop_rule:bool
    def __post_init__(self):
        if any(not isinstance(v,bool) for v in self.__dict__.values()):raise TypeError("preflight values")
    def failures(self):return tuple(sorted(k for k,v in self.__dict__.items() if not v))
    def passed(self):return not self.failures()
    def data(self):return {k:getattr(self,k) for k in sorted(self.__dict__)}
    canonical_data=data

@dataclass(frozen=True)
class TransitionReceipt:
    event:str; entity_id:str; before_sha256:str; after_sha256:str; occurred_at:str; rationale:str
    evidence_id:str|None=None; consequence_id:str|None=None; schema:str=RECEIPT_SCHEMA
    def __post_init__(self):
        if self.schema!=RECEIPT_SCHEMA:raise ValueError("receipt schema")
        object.__setattr__(self,"event",text("event",self.event)); object.__setattr__(self,"entity_id",ident("entity_id",self.entity_id))
        if not hash_ok(self.before_sha256) or not hash_ok(self.after_sha256):raise ValueError("receipt hash")
        object.__setattr__(self,"occurred_at",utc("occurred_at",self.occurred_at)); object.__setattr__(self,"rationale",text("rationale",self.rationale))
    def data(self):return {"schema":self.schema,"event":self.event,"entity_id":self.entity_id,"before_sha256":self.before_sha256,"after_sha256":self.after_sha256,"occurred_at":self.occurred_at,"rationale":self.rationale,"evidence_id":self.evidence_id,"consequence_id":self.consequence_id}
    canonical_data=data

@dataclass(frozen=True)
class SolverMandate:
    action_id:str; goal:str; constraints:tuple[str,...]; knowledge_ids:tuple[str,...]
    capabilities:tuple[str,...]; budget:tuple[tuple[str,str],...]; state_sha256:str
    issued_at:str; schema:str=MANDATE_SCHEMA
    def __post_init__(self):
        if self.schema!=MANDATE_SCHEMA:raise ValueError("mandate schema")
        object.__setattr__(self,"action_id",ident("action_id",self.action_id)); object.__setattr__(self,"goal",text("goal",self.goal))
        object.__setattr__(self,"constraints",seq("constraints",self.constraints,False)); object.__setattr__(self,"knowledge_ids",seq("knowledge_ids",self.knowledge_ids))
        object.__setattr__(self,"capabilities",seq("capabilities",self.capabilities))
        b=tuple(sorted((ident("budget key",k),text("budget value",v)) for k,v in self.budget))
        if len(b)!=len({k for k,_ in b}):raise ValueError("duplicate budget")
        object.__setattr__(self,"budget",b)
        if not hash_ok(self.state_sha256):raise ValueError("state_sha256")
        object.__setattr__(self,"issued_at",utc("issued_at",self.issued_at))
    def data(self):return {"schema":self.schema,"action_id":self.action_id,"goal":self.goal,"constraints":list(self.constraints),"knowledge_ids":list(self.knowledge_ids),"capabilities":list(self.capabilities),"budget":dict(self.budget),"state_sha256":self.state_sha256,"issued_at":self.issued_at}
    canonical_data=data
    def fingerprint(self):return fingerprint(self.data())

@dataclass(frozen=True)
class LoopState:
    knowledge:tuple[KnowledgeRecord,...]=(); actions:tuple[ActionRecord,...]=()
    evidence:tuple[EvidenceRecord,...]=(); consequences:tuple[ConsequenceRecord,...]=()
    receipts:tuple[TransitionReceipt,...]=(); schema:str=STATE_SCHEMA
    def __post_init__(self):
        if self.schema!=STATE_SCHEMA:raise ValueError("state schema")
        for n,t in (("knowledge",KnowledgeRecord),("actions",ActionRecord),("evidence",EvidenceRecord),("consequences",ConsequenceRecord),("receipts",TransitionReceipt)):
            vals=tuple(getattr(self,n))
            if any(not isinstance(x,t) for x in vals):raise TypeError(n)
            object.__setattr__(self,n,vals)
        ki=[x.knowledge_id for x in self.knowledge]; ai=[x.action_id for x in self.actions]; ei=[x.evidence_id for x in self.evidence]; ci=[x.consequence_id for x in self.consequences]
        for n,ids in (("knowledge",ki),("actions",ai),("evidence",ei),("consequences",ci)):
            if len(ids)!=len(set(ids)):raise ValueError(f"duplicate {n}")
        if set(ki)&set(ai):raise ValueError("knowledge/action overlap")
        ks,acs,es=set(ki),set(ai),set(ei)
        for e in self.evidence:
            if e.action_id not in acs:raise ValueError("orphan evidence")
        for c in self.consequences:
            if c.knowledge_id not in ks or (c.action_id is not None and c.action_id not in acs):raise ValueError("orphan consequence")
        for a in self.actions:
            if set(a.related_knowledge_ids)-ks or set(a.evidence_ids)-es:raise ValueError("orphan action reference")
        for k in self.knowledge:
            if set(k.evidence_ids)-es:raise ValueError("orphan knowledge evidence")
    def data(self,receipts=True):
        d={"schema":self.schema,"knowledge":[x.data() for x in sorted(self.knowledge,key=lambda x:x.knowledge_id)],"actions":[x.data() for x in sorted(self.actions,key=lambda x:x.action_id)],"evidence":[x.data() for x in sorted(self.evidence,key=lambda x:x.evidence_id)],"consequences":[x.data() for x in sorted(self.consequences,key=lambda x:x.consequence_id)]}
        if receipts:d["receipts"]=[x.data() for x in self.receipts]
        return d
    canonical_data=data
    def fingerprint(self):return fingerprint(self.data())
    def core_fingerprint(self):return fingerprint(self.data(False))
    def get_action(self,i):
        for x in self.actions:
            if x.action_id==i:return x
        raise KeyError(i)
    def get_knowledge(self,i):
        for x in self.knowledge:
            if x.knowledge_id==i:return x
        raise KeyError(i)
    def get_evidence(self,i):
        for x in self.evidence:
            if x.evidence_id==i:return x
        raise KeyError(i)
    def get_consequence(self,i):
        for x in self.consequences:
            if x.consequence_id==i:return x
        raise KeyError(i)

def receipt(before,after,event,entity,at,why,eid=None,cid=None):
    r=TransitionReceipt(event,entity,before.core_fingerprint(),after.core_fingerprint(),at,why,eid,cid)
    return replace(after,receipts=after.receipts+(r,))
def register_knowledge(s,k,*,occurred_at,rationale):
    if any(x.knowledge_id==k.knowledge_id for x in s.knowledge) or any(x.action_id==k.knowledge_id for x in s.actions):raise ValueError("duplicate/disjoint")
    return receipt(s,replace(s,knowledge=s.knowledge+(k,)),"REGISTER_KNOWLEDGE",k.knowledge_id,occurred_at,rationale)
def register_action(s,a,*,occurred_at,rationale):
    if any(x.action_id==a.action_id for x in s.actions) or any(x.knowledge_id==a.action_id for x in s.knowledge):raise ValueError("duplicate/disjoint")
    return receipt(s,replace(s,actions=s.actions+(a,)),"REGISTER_ACTION",a.action_id,occurred_at,rationale)
def record_consequence(s,c,*,occurred_at):
    if any(x.consequence_id==c.consequence_id for x in s.consequences):raise ValueError("duplicate consequence")
    s.get_knowledge(c.knowledge_id)
    if c.action_id:s.get_action(c.action_id)
    return receipt(s,replace(s,consequences=s.consequences+(c,)),"RECORD_CONSEQUENCE",c.knowledge_id,occurred_at,c.rationale,cid=c.consequence_id)
def repl_action(s,a):
    xs=tuple(a if x.action_id==a.action_id else x for x in s.actions)
    if xs==s.actions:raise KeyError(a.action_id)
    return replace(s,actions=xs)
def apply_knowledge_to_existing_action(s,cid,*,authorized_by,occurred_at,scheduled_at=None):
    c=s.get_consequence(cid)
    if c.verdict not in {Verdict.CHANGE,Verdict.MOVE,Verdict.KILL,Verdict.MERGE} or not c.action_id:raise ValueError("invalid consequence")
    a=s.get_action(c.action_id)
    if a.state in {ActionState.DOING,ActionState.DONE}:raise ValueError("cannot rewrite live/done")
    target=ActionState.TRASH if c.verdict is Verdict.KILL else c.target_state
    if target not in {ActionState.ASAP,ActionState.AT_A_DATE,ActionState.SOMEDAY_MAYBE,ActionState.TRASH}:raise ValueError("invalid target")
    if target is ActionState.AT_A_DATE and scheduled_at is None:raise ValueError("scheduled_at")
    na=replace(a,state=target,authorized_by=authorized_by if target in {ActionState.ASAP,ActionState.AT_A_DATE} else None,scheduled_at=scheduled_at if target is ActionState.AT_A_DATE else None,last_activity_at=None,related_knowledge_ids=seq("related_knowledge_ids",a.related_knowledge_ids+(c.knowledge_id,)),version=a.version+1)
    return receipt(s,repl_action(s,na),"APPLY_KNOWLEDGE_TO_ACTION",a.action_id,occurred_at,c.rationale,cid=cid)
def create_action_from_knowledge(s,cid,a,*,occurred_at):
    c=s.get_consequence(cid)
    if c.verdict is not Verdict.CREATE or a.state in {ActionState.DOING,ActionState.DONE} or c.knowledge_id not in a.related_knowledge_ids:raise ValueError("invalid creation")
    after=replace(s,actions=s.actions+(a,))
    return receipt(s,after,"CREATE_ACTION_FROM_KNOWLEDGE",a.action_id,occurred_at,c.rationale,cid=cid)
def start_action(s,aid,p,*,occurred_at):
    a=s.get_action(aid); at=utc("occurred_at",occurred_at)
    if a.state not in {ActionState.ASAP,ActionState.AT_A_DATE}:raise ValueError("not executable")
    if a.state is ActionState.AT_A_DATE and a.scheduled_at>at:raise ValueError("not due")
    if not p.passed():raise ValueError("preflight failed: "+",".join(p.failures()))
    na=replace(a,state=ActionState.DOING,last_activity_at=at,version=a.version+1)
    return receipt(s,repl_action(s,na),"START_ACTION",aid,at,"preflight passed")
def heartbeat_action(s,aid,*,occurred_at,observation):
    a=s.get_action(aid)
    if a.state is not ActionState.DOING:raise ValueError("not doing")
    na=replace(a,last_activity_at=utc("occurred_at",occurred_at),version=a.version+1)
    return receipt(s,repl_action(s,na),"HEARTBEAT_ACTION",aid,occurred_at,text("observation",observation))
def record_evidence(s,e):
    if any(x.evidence_id==e.evidence_id for x in s.evidence) or s.get_action(e.action_id).state is not ActionState.DOING:raise ValueError("invalid evidence")
    return receipt(s,replace(s,evidence=s.evidence+(e,)),"RECORD_EVIDENCE",e.action_id,e.occurred_at,e.observation,eid=e.evidence_id)
def complete_action(s,aid,eid,*,occurred_at):
    a=s.get_action(aid); e=s.get_evidence(eid)
    if a.state is not ActionState.DOING or e.action_id!=aid or not e.verified:raise ValueError("closure gate")
    na=replace(a,state=ActionState.DONE,last_activity_at=occurred_at,evidence_ids=seq("evidence_ids",a.evidence_ids+(eid,)),version=a.version+1)
    return receipt(s,repl_action(s,na),"COMPLETE_ACTION",aid,occurred_at,"verified closure",eid=eid)
def integrate_action_evidence_as_knowledge(s,eid,k,*,occurred_at):
    e=s.get_evidence(eid); a=s.get_action(e.action_id)
    if a.state is not ActionState.DONE or not e.verified or eid not in k.evidence_ids or e.generalizable_statement is None or k.statement!=e.generalizable_statement:raise ValueError("integration gate")
    after=replace(s,knowledge=s.knowledge+(k,))
    return receipt(s,after,"INTEGRATE_ACTION_EVIDENCE",k.knowledge_id,occurred_at,"verified reusable knowledge",eid=eid)
def issue_solver_mandate(s,aid,*,occurred_at,constraints,knowledge_ids,capabilities,budget):
    a=s.get_action(aid); at=utc("occurred_at",occurred_at)
    ok=a.state in {ActionState.ASAP,ActionState.DOING} or (a.state is ActionState.AT_A_DATE and a.scheduled_at<=at)
    if not ok or a.authorized_by is None:raise ValueError("solver cannot create authority")
    for k in knowledge_ids:s.get_knowledge(k)
    return SolverMandate(a.action_id,a.result_contract,tuple(constraints)+(a.change_contract,a.verification_contract),tuple(knowledge_ids),tuple(capabilities),tuple(budget.items()),s.core_fingerprint(),at)
def verify_receipt_chain(s):
    errors=[]
    for i,r in enumerate(s.receipts):
        if r.schema!=RECEIPT_SCHEMA:errors.append(f"receipt[{i}].schema")
        if r.before_sha256==r.after_sha256:errors.append(f"receipt[{i}].no_state_change")
    for a in s.actions:
        if a.state is ActionState.DOING and not a.last_activity_at:errors.append(f"action[{a.action_id}].liveness")
        if a.state is ActionState.DONE and not a.evidence_ids:errors.append(f"action[{a.action_id}].closure")
        if a.state is ActionState.SOMEDAY_MAYBE and a.last_activity_at:errors.append(f"action[{a.action_id}].hidden_execution")
    return tuple(errors)
