'use strict';
const {createStagingView}=require('./staging-pinned-score-adapter.cjs');
const {describeScoreRecord}=require('./score-display-guard-v2.cjs');
const {stagingScoreModel}=require('./staging-score-model-v2.cjs');
const {renderStagingScore}=require('./staging-score-renderer-v2.cjs');
function mount(container,overlay,id){
 return renderStagingScore(container,stagingScoreModel(overlay,id,createStagingView,describeScoreRecord));
}
module.exports={mount};
