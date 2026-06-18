"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __exportStar = (this && this.__exportStar) || function(m, exports) {
    for (var p in m) if (p !== "default" && !Object.prototype.hasOwnProperty.call(exports, p)) __createBinding(exports, m, p);
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.connectVpsWebSocket = exports.VpsClient = void 0;
var VpsClient_1 = require("./VpsClient");
Object.defineProperty(exports, "VpsClient", { enumerable: true, get: function () { return VpsClient_1.VpsClient; } });
var websocket_1 = require("./websocket");
Object.defineProperty(exports, "connectVpsWebSocket", { enumerable: true, get: function () { return websocket_1.connectVpsWebSocket; } });
__exportStar(require("./types"), exports);
