import React from 'react';

export default function ToggleSwitch({ id, checked, onChange, label }) {
  return (
    <div className="flex items-center">
      <div className="relative inline-block w-12 align-middle select-none">
        <input
          type="checkbox"
          id={id}
          name={id}
          className="toggle-checkbox absolute block w-6 h-6 rounded-full bg-white border-4 appearance-none cursor-pointer"
          checked={checked}
          onChange={onChange}
        />
        <label
          htmlFor={id}
          className="toggle-label block overflow-hidden h-6 rounded-full bg-gray-300 cursor-pointer"
        ></label>
      </div>
      {label && <span className="ml-2 text-sm text-gray-700">{label}</span>}
    </div>
  );
}