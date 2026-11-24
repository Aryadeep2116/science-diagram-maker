"""Keep structural checks separate from scientific review of a specific SVG."""
import hashlib

from checks import run_all_checks


def svg_digest(svg):
    return hashlib.sha256(svg.encode('utf-8')).hexdigest()


def assess_result(result, concept):
    """Refresh automatic checks and derive status without treating them as science proof.

    A recorded scientific verdict applies only to the exact SVG that was reviewed.
    """
    result = dict(result)
    svg = result.get('svg') or ''
    result['checks'] = run_all_checks(svg, concept)
    verification = result.get('scientific_verification') or {}
    if (verification.get('svg_sha256') != svg_digest(svg)
            or verification.get('status') not in ('pass', 'fail')):
        verification = {
            'status': 'unverified',
            'reason': 'Scientific accuracy and connectivity have not been verified by the automatic checks.',
        }
    result['scientific_verification'] = verification
    if any(not check['passed'] for check in result['checks'].values()) or verification['status'] == 'fail':
        result['final_status'] = 'fail'
    elif verification['status'] == 'pass':
        result['final_status'] = 'pass'
    else:
        result['final_status'] = 'needs_review'
    return result
