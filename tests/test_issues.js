const { test } = require('node:test');
const assert = require('node:assert/strict');
const { collectIssues } = require('../static/issues.js');
const checks = [['valid_xml', 'Valid XML'], ['in_viewbox', 'Inside viewBox']];

test('reports a scientific failure even if automatic checks pass', () => {
  const result = { checks: { valid_xml: {passed: true}, in_viewbox: {passed: true} },
    scientific_verification: {status: 'fail', reason: 'Wire is disconnected.'} };
  assert.deepEqual(collectIssues(result, checks), [{category: 'Scientific verification', label: 'Scientific review', reason: 'Wire is disconnected.'}]);
});

test('reports the real automatic failure but not skipped follow-up checks', () => {
  const result = {checks: {valid_xml: {passed: false, reason: 'Broken XML'},
    in_viewbox: {passed: false, reason: 'Skipped because the SVG could not be parsed.'}}};
  assert.deepEqual(collectIssues(result, checks).map(issue => issue.reason), ['Broken XML']);
});

test('unverified is not a failure, but missing checks and request errors are reported', () => {
  const result = {checks: {valid_xml: {passed: true}}, scientific_verification: {status: 'unverified'}};
  const issues = collectIssues(result, checks, 'Request timed out');
  assert.deepEqual(issues.map(issue => issue.reason), ['No check result is available.', 'Request timed out']);
  assert.equal(collectIssues({checks: {valid_xml: {passed: true}, in_viewbox: {passed: true}}, scientific_verification: {status: 'unverified'}}, checks).length, 0);
});
