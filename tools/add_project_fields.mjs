// 主要作用：为工程审计数据库的三张表统一补充项目名称和项目编号，并导出可复核的工作簿副本。

import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath = "Database/工作簿2_K公司8项目完整模拟数据.xlsx";
const outputPath = "outputs/工作簿2_K公司8项目完整模拟数据_已补充项目字段.xlsx";
const previewDir = "outputs/project_fields_preview";

async function loadWorkbook() {
  const input = await FileBlob.load(inputPath);
  return SpreadsheetFile.importXlsx(input);
}

async function saveRender(workbook, sheetName, range, outputName) {
  const preview = await workbook.render({ sheetName, range, scale: 1, format: "png" });
  await fs.writeFile(`${previewDir}/${outputName}`, new Uint8Array(await preview.arrayBuffer()));
}

function buildProjectMaps(infoValues) {
  const byContract = new Map();
  const byName = new Map();
  for (const row of infoValues.slice(1)) {
    const projectNumber = row[0];
    const projectName = row[1];
    const contractNumber = `K-HT-${String(projectNumber).slice(1)}`;
    const value = [projectName, projectNumber];
    byContract.set(contractNumber, value);
    byName.set(projectName, value);
  }
  return { byContract, byName };
}

async function main() {
  await fs.mkdir(previewDir, { recursive: true });
  const workbook = await loadWorkbook();
  const info = workbook.worksheets.getItem("项目信息");
  const design = workbook.worksheets.getItem("设计变更");
  const committee = workbook.worksheets.getItem("技术委员会评审");

  await saveRender(workbook, "项目信息", "A1:J9", "before_project_info.png");
  await saveRender(workbook, "设计变更", "A1:AC12", "before_design_change.png");
  await saveRender(workbook, "技术委员会评审", "A1:J9", "before_committee.png");

  const infoValues = info.getRange("A1:J9").values;
  const { byContract, byName } = buildProjectMaps(infoValues);

  info.getRange("A1").values = [["项目编号"]];

  design.getRange("AD2:AE84").copyFrom(design.getRange("C2:D84"), "all");
  design.getRange("AD2:AE2").values = [["项目名称", "项目编号"]];
  const designValues = design.getRange("C5:C84").values;
  const designProjectValues = designValues.map(([contractNumber]) => {
    if (contractNumber === null || contractNumber === undefined || contractNumber === "") {
      return [null, null];
    }
    return byContract.get(contractNumber);
  });
  design.getRange("AD5:AE84").values = designProjectValues;
  design.getRange("AD1:AD84").format.columnWidth = 30;
  design.getRange("AE1:AE84").format.columnWidth = 18;

  committee.getRange("K2:L9").copyFrom(committee.getRange("B2:C9"), "all");
  committee.getRange("K2:L2").values = [["项目名称", "项目编号"]];
  const committeeNames = committee.getRange("B3:B9").values;
  const committeeProjectValues = committeeNames.map(([projectName]) => byName.get(projectName));
  committee.getRange("K3:L9").values = committeeProjectValues;
  committee.getRange("K1:K9").format.columnWidth = 30;
  committee.getRange("L1:L9").format.columnWidth = 18;

  const verification = await workbook.inspect({
    kind: "table",
    range: "项目信息!A1:J9",
    include: "values,formulas",
    tableMaxRows: 12,
    tableMaxCols: 12,
    maxChars: 12000,
  });
  console.log("VERIFY_PROJECT_INFO");
  console.log(verification.ndjson);

  const designVerification = await workbook.inspect({
    kind: "table",
    range: "设计变更!C2:AE8",
    include: "values,formulas",
    tableMaxRows: 12,
    tableMaxCols: 35,
    maxChars: 16000,
  });
  console.log("VERIFY_DESIGN_CHANGE");
  console.log(designVerification.ndjson);

  const committeeVerification = await workbook.inspect({
    kind: "table",
    range: "技术委员会评审!B2:L9",
    include: "values,formulas",
    tableMaxRows: 12,
    tableMaxCols: 15,
    maxChars: 12000,
  });
  console.log("VERIFY_COMMITTEE");
  console.log(committeeVerification.ndjson);

  const errors = await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
    options: { useRegex: true, maxResults: 300 },
    summary: "formula error scan after project field edit",
  });
  console.log("FORMULA_ERRORS");
  console.log(errors.ndjson);

  await saveRender(workbook, "项目信息", "A1:J9", "after_project_info.png");
  await saveRender(workbook, "设计变更", "A1:AE12", "after_design_change.png");
  await saveRender(workbook, "技术委员会评审", "A1:L9", "after_committee.png");

  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(outputPath);
  console.log(`EXPORTED ${outputPath}`);
}

await main();
