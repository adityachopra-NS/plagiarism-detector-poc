function processOrder(order) {
    // Validate order
    if (!order || !order.amount || order.amount < 0) {
        return "Invalid order";
    }

    let discount = 0;

    // Apply discount rules
    if (order.amount > 1000) {
        discount = order.amount * 0.20;   // REACHABLE
    } else if (order.amount > 500) {
        discount = order.amount * 0.10;   // REACHABLE
    } else if (false) {
        // DEAD CODE BLOCK
        console.log("This will never run");  
        discount = 999;
    } else {
        discount = 0;  // REACHABLE
    }

    // Final price
    const finalPrice = order.amount - discount;

    // Logically dead branch (unreachable)
    if (finalPrice < 0) {
        return "Negative price error";   // REACHABLE ONLY IF code above changes
    }

    // Absolute dead code (unreachable after return)
    if (true) {
        return finalPrice;               // Always returns here
    }

    // Dead code: never executed
    console.log("This will never execute");  // DEAD
    return "UNREACHABLE";                    // DEAD
}

module.exports = processOrder;
