"""Certificates for LP-KAL v1."""
from __future__ import annotations
import hashlib, json
from typing import Any
from .model import LoopState, SolverMandate, canonical_json, verify_receipt_chain

SCHEMA="logic-power-knowledge-action-loop/certificate/1"
STATUSES={"PASS","PASS_CON_LIMITES","PARTIAL","FAIL","BLOCKED","NO_EVALUABLE","REVERTED"}

def digest(value:Any)->str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()

def build_certificate(*,state:LoopState,status:str,result:dict[str,Any],mandates:tuple[SolverMandate,...]=())->dict[str,Any]:
    if status not in STATUSES:raise ValueError("unsupported status")
    errors=list(verify_receipt_chain(state))
    if status=="PASS" and errors:raise ValueError("PASS forbidden with errors")
    payload={"status":status,"state_sha256":state.fingerprint(),"core_state_sha256":state.core_fingerprint(),"receipt_count":len(state.receipts),"receipt_errors":errors,"mandates":[m.canonical_data() for m in mandates],"result":result}
    return {"schema":SCHEMA,"payload":payload,"payload_sha256":digest(payload)}

def verify_certificate(certificate:dict[str,Any])->tuple[str,...]:
    errors=[]
    if not isinstance(certificate,dict):return ("certificate",)
    if certificate.get("schema")!=SCHEMA:errors.append("schema")
    payload=certificate.get("payload")
    if not isinstance(payload,dict):return tuple(errors+["payload"])
    try: expected=digest(payload)
    except (TypeError,ValueError):errors.append("payload-canonical"); expected=None
    if certificate.get("payload_sha256")!=expected:errors.append("payload-hash")
    if payload.get("status") not in STATUSES:errors.append("status")
    for name in ("state_sha256","core_state_sha256"):
        value=payload.get(name)
        if not isinstance(value,str) or len(value)!=64 or any(c not in "0123456789abcdef" for c in value):errors.append(name)
    count=payload.get("receipt_count")
    if isinstance(count,bool) or not isinstance(count,int) or count<0:errors.append("receipt-count")
    receipt_errors=payload.get("receipt_errors")
    if not isinstance(receipt_errors,list) or any(not isinstance(x,str) for x in receipt_errors):errors.append("receipt-errors")
    elif payload.get("status")=="PASS" and receipt_errors:errors.append("pass-with-errors")
    if not isinstance(payload.get("mandates"),list):errors.append("mandates")
    if not isinstance(payload.get("result"),dict):errors.append("result")
    return tuple(errors)

def canonical_certificate_json(certificate:dict[str,Any])->str:
    return json.dumps(certificate,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)
