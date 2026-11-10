// Browser-local, end-of-day shortfall summary; no banking or financial determinations.
// Works on projected daily balances, not pending transactions or intraday funds.
import {dateUTC,LIMITS} from './engine.mjs';
const DAY=86_400_000;
export function summarizeShortfalls(projection){
  if(!projection||!Array.isArray(projection.days)||projection.days.length<1||projection.days.length>LIMITS.days)
    throw Error('Expected 1–366 projected days.');
  let previousTime=null,previousDate=null,runStart=null,runDays=0;
  let daysBelowZero=0,firstBelowZeroDate=null,lowestBalanceCents=null,longestRunDays=0;
  const periods=[];
  const finishRun=()=>{
    if(runStart===null)return;
    periods.push({start:runStart,end:previousDate,days:runDays});
    longestRunDays=Math.max(longestRunDays,runDays);
    runStart=null;runDays=0;
  };
  for(const day of projection.days){
    if(!day||typeof day.date!=='string'||!Number.isSafeInteger(day.balanceCents)||
       Math.abs(day.balanceCents)>LIMITS.maxAbsCents)throw Error('Invalid projected day or balance.');
    const time=dateUTC(day.date);
    if(previousTime!==null&&time-previousTime!==DAY)throw Error('Projected dates must be consecutive.');
    if(day.balanceCents<0){
      daysBelowZero++;
      if(firstBelowZeroDate===null)firstBelowZeroDate=day.date;
      if(lowestBalanceCents===null||day.balanceCents<lowestBalanceCents)lowestBalanceCents=day.balanceCents;
      if(runStart===null)runStart=day.date;
      runDays++;
    }else finishRun();
    previousTime=time;previousDate=day.date;
  }
  finishRun();
  return {daysBelowZero,firstBelowZeroDate,lowestBalanceCents,longestRunDays,periods};
}


// Compare *the same calendar dates* in two projections. A date that becomes
// nonnegative is not proof a payment will clear or a bank will avoid fees.
export function compareBelowZeroDates(baseline,scenario){
  summarizeShortfalls(baseline);
  summarizeShortfalls(scenario);
  if(baseline.days.length!==scenario.days.length)
    throw Error('Scenarios must cover the same projected dates.');
  let noLongerBelowZero=0,newlyBelowZero=0,stillBelowZero=0,nonnegativeInBoth=0;
  let firstNoLongerBelowZeroDate=null,firstNewlyBelowZeroDate=null;
  for(let i=0;i<baseline.days.length;i++){
    const a=baseline.days[i],b=scenario.days[i];
    if(a.date!==b.date)throw Error('Scenarios must cover the same projected dates.');
    const wasBelow=a.balanceCents<0,isBelow=b.balanceCents<0;
    if(wasBelow&&isBelow)stillBelowZero++;
    else if(wasBelow){
      noLongerBelowZero++;
      if(firstNoLongerBelowZeroDate===null)firstNoLongerBelowZeroDate=a.date;
    }else if(isBelow){
      newlyBelowZero++;
      if(firstNewlyBelowZeroDate===null)firstNewlyBelowZeroDate=a.date;
    }else nonnegativeInBoth++;
  }
  return {noLongerBelowZero,newlyBelowZero,stillBelowZero,nonnegativeInBoth,
    firstNoLongerBelowZeroDate,firstNewlyBelowZeroDate};
}
