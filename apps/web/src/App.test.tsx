import { render, screen } from "@testing-library/react";

import { App } from "./App";

describe("App", () => {
  it("shows the independent project boundary", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "FlopBench" })).toBeInTheDocument();
    expect(screen.getByText(/independent community project/i)).toBeInTheDocument();
    expect(screen.getByText(/not an official FLOP Labs/i)).toBeInTheDocument();
  });

  it("states that stage zero performs no scan or request", () => {
    render(<App />);

    expect(screen.getByText(/no system scan or network request/i)).toBeInTheDocument();
  });
});
