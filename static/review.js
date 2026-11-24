// A browser verdict applies only to the exact SVG. It never overrides checks.
function withBrowserReview(result, review) {
  if (!review || review.svg !== result.svg || !review.reviewedAt ||
      !['pass', 'fail'].includes(review.scientificStatus)) return result;
  const expected = ['valid_xml', 'in_viewbox', 'animated_bounds', 'title_and_labels', 'has_animation', 'custom_checks'];
  const checkMap = result.checks || {};
  const checks = expected.map(key => checkMap[key] || { passed: null });
  const finalStatus = checks.some(check => check.passed === false) || review.scientificStatus === 'fail'
    ? 'fail' : checks.some(check => check.passed !== true) ? 'needs_review' : 'pass';
  return {
    ...result,
    final_status: finalStatus,
    scientific_verification: {
      status: review.scientificStatus,
      reason: review.note ? `Browser reviewer: ${review.note}` : 'Explicitly reviewed in this browser.',
      method: `Browser-local review recorded ${review.reviewedAt}. This is not a shared server verdict.`,
    },
  };
}
if (typeof module !== 'undefined' && module.exports) module.exports = { withBrowserReview };
