import { r as decode, i as encode, n as init } from './mapp-aVEcQ73U.js';
import fs from 'fs';

async function main() {
    const action = process.argv[2]; // "encode" or "decode"
    const key = process.argv[3];

    if (!action || !key) {
        console.error("Usage: node codec.js <encode|decode> <key>");
        process.exit(1);
    }

    // Read all from stdin
    const data = fs.readFileSync(0, 'utf-8').trim();

    try {
        await init();
        if (action === "encode") {
            const result = encode(data, key);
            process.stdout.write(result);
        } else if (action === "decode") {
            const result = decode(data, key);
            process.stdout.write(result);
        } else {
            console.error("Unknown action:", action);
            process.exit(1);
        }
    } catch (e) {
        console.error("Error:", e.message || e);
        process.exit(1);
    }
}

main();
