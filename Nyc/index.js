const { helperA } = require("./utilA");
const { helperB } = require("./utilB");

function main() {
  console.log("Inside main()");
  const resultA = helperA(10);
  console.log("Result A:", resultA);

  // NOTE: We are NOT using helperB intentionally
}

main();
