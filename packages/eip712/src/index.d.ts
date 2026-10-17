// SPDX-License-Identifier: Apache-2.0
// Declarations of the EIP-712 encoder of PayTrue. The implementation is generated from eip712/types.json (a PROPOSAL, not frozen).

export type Value = string | number | bigint | boolean | Value[] | { [k: string]: Value };

export function keccak256(data: Uint8Array): Uint8Array;
export function utf8(s: string): Uint8Array;
export function concat(...parts: Uint8Array[]): Uint8Array;
export function hex(b: Uint8Array): string;
export function fromHex(h: string): Uint8Array;
export function u256(n: bigint): Uint8Array;

export function encodeType(name: string): string;
export function typeHash(name: string): Uint8Array;
export function hashStruct(name: string, value: { [k: string]: Value }): Uint8Array;
export function domainSeparator(domain: "mandates" | "quote", chainId: bigint, verifyingContract: string): Uint8Array;
export function digest(separator: Uint8Array, structHash: Uint8Array): Uint8Array;
export function tag(name: "LINEAGE_TAG" | "MANDATE_TAG" | "CYCLE_TAG" | "ROUTE_DIRECT_TAG" | "SNAPSHOT_TAG" | "PIN_EOA"): Uint8Array;

export function witnessTypeString(): string;
export function permit2DomainSeparator(chainId: bigint, permit2: string): Uint8Array;
export interface WitnessInput {
  token: string;
  amount: bigint;
  spender: string;
  nonce: bigint;
  deadline: bigint;
  witness: { [k: string]: Value };
  extra?: Array<{ token: string; amount: bigint }>;
}
export function permit2WitnessHash(input: WitnessInput, batch: boolean): { typeHash: Uint8Array; hash: Uint8Array };

export interface SnapshotArgs {
  lineageId: string;
  predecessorId: string;
  generation: number | string | bigint;
  customer: string;
}
export function snapshotWords(args: SnapshotArgs, terms: { [k: string]: Value }): Uint8Array[];
export function snapshotHash(args: SnapshotArgs, terms: { [k: string]: Value }): Uint8Array;

export namespace types {
  type Field = readonly [type: string, name: string];
  const STATUS: string;
  const SPEC_VERSION: string;
  const DOMAIN_TYPE: string;
  const DOMAINS: { readonly mandates: { readonly name: string; readonly version: string }; readonly quote: { readonly name: string; readonly version: string } };
  const BOUNDS: Readonly<Record<string, number>>;
  const TAGS: Readonly<Record<string, string>>;
  const STRUCTS: Record<string, { domain: string; fields: readonly Field[]; boundedArrays: Record<string, string> }>;
  const PERMIT2_WITNESS: Readonly<Record<string, string>>;
  const SNAPSHOT: Readonly<Record<string, unknown>>;
  const TYPEHASHES: Record<string, string>;
}
