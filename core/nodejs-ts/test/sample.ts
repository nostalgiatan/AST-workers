// Test file for ast-ts
import { Project } from 'ts-morph';

export function hello(name: string): string {
  return `Hello, ${name}!`;
}

export class UserService {
  private users: string[] = [];

  addUser(name: string): void {
    this.users.push(name);
  }

  getUsers(): string[] {
    return this.users;
  }

    readonly maxUsers: number = 100;
}

export function identity<T>(value: T): T {
    return value
}

export function first<T extends Array<any>>(arr: T): T[0] {
    return arr[0]
}

export interface IEntity<ID> {
}

export type Point = { x: number; y: number };

export enum Color {
    Red,
    Green,
    Blue
}

export const VERSION: string = "1.0.0";

export function identity<T>(value: T): T {
    return value
}

export interface IEntity<ID> {
}

export type Point = { x: number; y: number };

export enum Color {
    Red,
    Green,
    Blue
}

export const VERSION: string = "1.0.0";

export interface IUser {
    id: string;
    name: string;
    email?: string;
}

export enum Status {
    Pending,
    Active,
    Inactive
}

export type UserID = string | number;
export type TestID = string | number;

export enum Priority {
    Low,
    Medium,
    High
}

export abstract class Repository<T> implements IUser {
}

export abstract class TestEntity<T> extends IUser {
}

export function genericFunc<T>(value: T): T {
    return value
}

export class DataManager<T> extends UserService implements IUser {
}

export interface IProduct {
    id: string;
    name: string;
    price?: number;
}

export type JSONValue = string | number | boolean | object | null;

export enum Role {
    Admin,
    User,
    Guest
}
