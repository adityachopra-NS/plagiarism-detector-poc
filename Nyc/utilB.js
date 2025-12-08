function helperB(num) {
  console.log("Running helperB"); // this will never execute
  return num * 100;
}

function unusedFunction() {
  return "I am unused";
}

module.exports = { helperB, unusedFunction };
