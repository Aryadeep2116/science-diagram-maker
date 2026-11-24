const { test } = require('node:test');
const assert = require('node:assert/strict');
const { withBrowserReview } = require('../static/review.js');
const keys = ['valid_xml', 'in_viewbox', 'animated_bounds', 'title_and_labels', 'has_animation', 'custom_checks'];
const checks = () => Object.fromEntries(keys.map(key => [key, {passed: true}]));
const base = () => ({svg: '<svg/>', checks: checks(), final_status: 'needs_review', scientific_verification: {status:'unverified'}});
const review = () => ({svg:'<svg/>', scientificStatus:'pass', reviewedAt:'2026-01-01T00:00:00Z', note:'I inspected it'});

test('explicit review records a pass for the exact SVG when checks pass', () => {
  const result = withBrowserReview(base(), review());
  assert.equal(result.final_status, 'pass');
  assert.equal(result.scientific_verification.status, 'pass');
  assert.match(result.scientific_verification.method, /Browser-local/);
});
test('review cannot override failed, missing or unverified checks', () => {
  for (const value of [false, null, undefined]) {
    const input = base();
    if (value === undefined) delete input.checks.in_viewbox;
    else input.checks.in_viewbox.passed = value;
    assert.equal(withBrowserReview(input, review()).final_status, value === false ? 'fail' : 'needs_review');
  }
});
test('old, different SVG or non-explicit decision cannot be a scientific verdict', () => {
  const input = base();
  assert.equal(withBrowserReview(input, {...review(), svg:'<svg>changed</svg>'}), input);
  assert.equal(withBrowserReview(input, {...review(), reviewedAt:null}), input);
});
test('explicit rejection fails even if automatic checks pass', () => {
  assert.equal(withBrowserReview(base(), {...review(), scientificStatus:'fail'}).final_status, 'fail');
});
