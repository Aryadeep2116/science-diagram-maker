// Summarise known failures without treating an unreviewed diagram as a failure.
function collectIssues(result, checks, requestError) {
  const issues = [];
  for (const [key, label] of checks) {
    const check = (result.checks || {})[key];
    if (!check) {
      issues.push({ category: 'Automatic check', label, reason: 'No check result is available.' });
    } else if (!check.passed && !String(check.reason || '').startsWith('Skipped')) {
      issues.push({ category: 'Automatic check', label, reason: check.reason || 'No reason was provided.' });
    }
  }
  const verification = result.scientific_verification || {};
  if (verification.status === 'fail') {
    issues.push({ category: 'Scientific verification', label: 'Scientific review',
      reason: verification.reason || 'No reason was provided.' });
  }
  if (requestError) {
    issues.push({ category: 'Generation', label: 'Live generation', reason: requestError });
  }
  return issues;
}

if (typeof module !== 'undefined' && module.exports) module.exports = { collectIssues };
