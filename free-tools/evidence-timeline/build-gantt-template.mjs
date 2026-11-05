import fs from 'node:fs/promises';
import {Workbook, SpreadsheetFile} from '@oai/artifact-tool';
// Run with the primary artifact runtime, with its node_modules linked in a writable temp directory.
const outputDir=process.argv[2];
if(!outputDir?.startsWith('/'))throw Error('Provide an absolute output directory.');
const wb=Workbook.create();
const gantt=wb.worksheets.add('Gantt');
const entries=wb.worksheets.add('Entries');
for(const sheet of [gantt,entries]) {
  sheet.showGridLines=false;
  sheet.getRange('A1:AB10').format={font:{name:'Arial',size:11,color:'#223D33'},verticalAlignment:'center'};
  sheet.getRange('A2:AB2').format.font={name:'Arial',size:16,bold:true,color:'#164737'};
  sheet.getRange('A3:AB7').format.font={name:'Arial',size:11,color:'#4D6257'};
  for(let row=2;row<=7;row++)sheet.mergeCells(`A${row}:J${row}`);
  sheet.getRange('A2').values=[['Evidence timeline']];
  sheet.getRange('A3').values=[['All entries • 2 entries']];
  sheet.getRange('A4').values=[['Jan 12, 2026 – Jan 20, 2026']];
  sheet.getRange('A5').values=[['◆ Single-day milestone    ■ Date range']];
  sheet.getRange('A6').values=[['Edit Start / End dates to update bars. Complete text and labels are on Entries.']];
  sheet.getRange('A7').values=[['Each column covers 1 calendar day. Re-export to change the chart range.']];
  sheet.getRange('A2:AB7').format.rowHeight=25;
  sheet.getRange('A8:AB8').format={fill:'#245943',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},rowHeight:30,horizontalAlignment:'center'};
  sheet.getRange('A9:AB9').format={fill:'#F2F5EF',rowHeight:44,wrapText:true};
  sheet.getRange('A10:AB10').format={fill:'#FFFFFF',rowHeight:44,wrapText:true};
  sheet.getRange('A:A').format.columnWidth=25;
  sheet.getRange('B:B').format.columnWidth=49;
  sheet.getRange('C:D').format.columnWidth=17;
  sheet.getRange('E:AB').format.columnWidth=17;
  sheet.freezePanes.freezeRows(8);
}
gantt.tabColor='#245943';
gantt.freezePanes.freezeColumns(2);
gantt.getRange('A8:D8').values=[['Source reference','Description','Start','End']];
gantt.getRange('C9:D10').setNumberFormat('mmm d, yyyy');
gantt.getRange('C9:D10').format.fill='#FFF3D6';
gantt.getRange('E8:AB8').setNumberFormat('mmm d, yyyy');
gantt.getRange('E9:AB10').format.horizontalAlignment='center';
gantt.getRange('E9:AB10').conditionalFormats.add('cellIs',{operator:'equal',formula:'"■"',format:{fill:'#377B5D',font:{color:'#377B5D'}}});
gantt.getRange('E9:AB10').conditionalFormats.add('cellIs',{operator:'equal',formula:'"◆"',format:{fill:'#EDE6F1',font:{color:'#755180',bold:true}}});
gantt.getRange('A9:D10').values=[['NOTES-01','A fictional review period',46034,46038],['EMAIL-02','A fictional milestone',46039,46039]];
for(let col=4;col<28;col++) {
  gantt.getCell(7,col).values=[[46034+col-4]];
  for(let row=8;row<10;row++) {
    const ref=String.fromCharCode(65+col);
    if(col<26)gantt.getCell(row,col).formulas=[[`=IF(AND($C${row+1}<=${ref}$8,$D${row+1}>=${ref}$8),IF($C${row+1}=$D${row+1},"◆","■"),"")`]];
  }
}
entries.getRange('A8:H8').values=[['Source reference','Start','End (optional)','Full description','Review status','Entry type','Group','Date type']];
entries.getRange('A9:H10').values=[['NOTES-01',46034,46038,'A fictional review period','reported','source','review','Range'],['EMAIL-02',46039,null,'A fictional milestone','reported','source','review','Milestone']];
entries.getRange('A6').values=[['Original source text is retained as text. Gantt dates can be edited separately.']];
entries.getRange('A7').values=[['Sources: the entries supplied by the person preparing this workbook.']];
entries.getRange('B9:C10').setNumberFormat('mmm d, yyyy');
entries.getRange('B:C').format.columnWidth=17;
entries.getRange('D:D').format.columnWidth=70;
entries.getRange('E:H').format.columnWidth=23;
wb.recalculate();
await fs.mkdir(outputDir,{recursive:true});
await (await SpreadsheetFile.exportXlsx(wb)).save(`${outputDir}/gantt-template.xlsx`);
const preview=await wb.render({sheetName:'Gantt',range:'A1:L10',scale:1,format:'png'});
await fs.writeFile(`${outputDir}/template-preview.png`,new Uint8Array(await preview.arrayBuffer()));
console.log((await wb.inspect({kind:'region',sheetId:'Gantt',range:'A8:H10',maxChars:1500,tableMaxCols:8})).ndjson);
