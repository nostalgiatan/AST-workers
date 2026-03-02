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
}

export function goodbye(name: string): string {
    return `Goodbye, ${name}!`
}
