export function weightedScore(criteria, ratings) {
  if (criteria.length === 0) throw Error('Criteria required');
  const totalWeight = criteria.reduce((sum, c) => sum + c.weight, 0);
  if (totalWeight !== 100) throw Error('Weights must total 100');
  let points = 0;
  for (const c of criteria) {
    const rating = ratings.find(r => r.criterionId === c.id);
    if (!rating || !Number.isInteger(rating.score) || rating.score < 0 || rating.score > 5 || !rating.evidenceRef) return null;
    points += c.weight * rating.score;
  }
  return points / 5;
}
