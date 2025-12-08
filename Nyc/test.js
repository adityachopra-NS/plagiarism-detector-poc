const processOrder = require("./orderProcessor");
const assert = require("assert");

describe("Order Processor", () => {
    it("should process small order", () => {
        assert.equal(processOrder({ amount: 100 }), 100);
    });

    it("should process medium order", () => {
        assert.equal(processOrder({ amount: 600 }), 540);
    });
});
