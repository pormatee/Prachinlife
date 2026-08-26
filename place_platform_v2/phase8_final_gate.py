from __future__ import annotations

def evaluate_phase8_final_gate(report):
    checks=dict(report.get('checks') or {})
    checks.update({
      'phase7_decision_layer_present':report.get('checks',{}).get('decision_assistant_preserved') is True,
      'scale_without_fork':report.get('scale',{}).get('same_frontend_codebase') is True,
      'privacy_boundary_explicit':report.get('safety',{}).get('personal_data_persisted') is False,
      'explicit_adoption_still_required':report.get('safety',{}).get('automatic_adoption') is False,
    })
    return {'status':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'v2_complete':all(checks.values())}
