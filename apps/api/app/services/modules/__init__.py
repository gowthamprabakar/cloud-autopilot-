"""
Simulation Modules — Sprint 33 + Sprint 34.

Sprint 33 (Core Domains):
  CSPM: Cloud Security Posture Management
  CWPP: Cloud Workload Protection Platform
  DSPM: Data Security Posture Management
  KSPM: Kubernetes Security Posture Management
  ASM:  Attack Surface Management

Sprint 34 (Gap Domains):
  Quantum:      Quantum Cryptography Harvest Attack (HNDL) risk assessment
  Deepfake:     AI Deepfake Identity Fraud simulation
  SupplyChain:  AI-Accelerated Supply Chain Firmware Attack simulation
  OTICS:        OT/ICS Critical Infrastructure Convergence
  LLMjacking:   LLMjacking Cloud AI Credential Abuse
  FederatedID:  Federated Identity Cross-Cloud Abuse
"""

from .cspm_module import CSPMModule
from .cwpp_module import CWPPModule
from .dspm_module import DSPMModule
from .kspm_module import KSPMModule
from .asm_module import ASMModule
from .quantum_module import QuantumModule
from .deepfake_module import DeepfakeModule
from .supply_chain_module import SupplyChainModule
from .ot_ics_module import OTICSModule
from .llmjacking_module import LLMjackingModule
from .federated_id_module import FederatedIDModule

__all__ = [
    "CSPMModule",
    "CWPPModule",
    "DSPMModule",
    "KSPMModule",
    "ASMModule",
    "QuantumModule",
    "DeepfakeModule",
    "SupplyChainModule",
    "OTICSModule",
    "LLMjackingModule",
    "FederatedIDModule",
]
