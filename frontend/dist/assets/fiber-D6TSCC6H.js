import{r as b,a as V,g as C,R as k}from"./react-CIP6LD3P.js";var j={exports:{}},E={};/**
 * @license React
 * react-jsx-runtime.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */var z=b,W=Symbol.for("react.element"),A=Symbol.for("react.fragment"),F=Object.prototype.hasOwnProperty,L=z.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED.ReactCurrentOwner,U={key:!0,ref:!0,__self:!0,__source:!0};function D(e,t,r){var o,n={},u=null,a=null;r!==void 0&&(u=""+r),t.key!==void 0&&(u=""+t.key),t.ref!==void 0&&(a=t.ref);for(o in t)F.call(t,o)&&!U.hasOwnProperty(o)&&(n[o]=t[o]);if(e&&e.defaultProps)for(o in t=e.defaultProps,t)n[o]===void 0&&(n[o]=t[o]);return{$$typeof:W,type:e,key:u,ref:a,props:n,_owner:L.current}}E.Fragment=A;E.jsx=D;E.jsxs=D;j.exports=E;var me=j.exports,h={},R=V;h.createRoot=R.createRoot,h.hydrateRoot=R.hydrateRoot;const M={},g=e=>{let t;const r=new Set,o=(s,l)=>{const c=typeof s=="function"?s(t):s;if(!Object.is(c,t)){const i=t;t=l??(typeof c!="object"||c===null)?c:Object.assign({},t,c),r.forEach(f=>f(t,i))}},n=()=>t,p={setState:o,getState:n,getInitialState:()=>m,subscribe:s=>(r.add(s),()=>r.delete(s)),destroy:()=>{(M?"production":void 0)!=="production"&&console.warn("[DEPRECATED] The `destroy` method will be unsupported in a future version. Instead use unsubscribe function returned by subscribe. Everything will be garbage-collected if store is garbage-collected."),r.clear()}},m=t=e(o,n,p);return p},N=e=>e?g(e):g;var O={exports:{}},$={},I={exports:{}},P={};/**
 * @license React
 * use-sync-external-store-shim.production.js
 *
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */var d=b;function B(e,t){return e===t&&(e!==0||1/e===1/t)||e!==e&&t!==t}var G=typeof Object.is=="function"?Object.is:B,J=d.useState,Y=d.useEffect,H=d.useLayoutEffect,K=d.useDebugValue;function Q(e,t){var r=t(),o=J({inst:{value:r,getSnapshot:t}}),n=o[0].inst,u=o[1];return H(function(){n.value=r,n.getSnapshot=t,S(n)&&u({inst:n})},[e,r,t]),Y(function(){return S(n)&&u({inst:n}),e(function(){S(n)&&u({inst:n})})},[e]),K(r),r}function S(e){var t=e.getSnapshot;e=e.value;try{var r=t();return!G(e,r)}catch{return!0}}function X(e,t){return t()}var Z=typeof window>"u"||typeof window.document>"u"||typeof window.document.createElement>"u"?X:Q;P.useSyncExternalStore=d.useSyncExternalStore!==void 0?d.useSyncExternalStore:Z;I.exports=P;var q=I.exports;/**
 * @license React
 * use-sync-external-store-shim/with-selector.production.js
 *
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */var y=b,ee=q;function te(e,t){return e===t&&(e!==0||1/e===1/t)||e!==e&&t!==t}var re=typeof Object.is=="function"?Object.is:te,oe=ee.useSyncExternalStore,ne=y.useRef,ue=y.useEffect,se=y.useMemo,ie=y.useDebugValue;$.useSyncExternalStoreWithSelector=function(e,t,r,o,n){var u=ne(null);if(u.current===null){var a={hasValue:!1,value:null};u.current=a}else a=u.current;u=se(function(){function p(i){if(!m){if(m=!0,s=i,i=o(i),n!==void 0&&a.hasValue){var f=a.value;if(n(f,i))return l=f}return l=i}if(f=l,re(s,i))return f;var _=o(i);return n!==void 0&&n(f,_)?(s=i,f):(s=i,l=_)}var m=!1,s,l,c=r===void 0?null:r;return[function(){return p(t())},c===null?void 0:function(){return p(c())}]},[t,r,o,n]);var v=oe(e,u[0],u[1]);return ue(function(){a.hasValue=!0,a.value=v},[v]),ie(v),v};O.exports=$;var ae=O.exports;const ce=C(ae),T={},{useDebugValue:fe}=k,{useSyncExternalStoreWithSelector:le}=ce;let w=!1;const de=e=>e;function ve(e,t=de,r){(T?"production":void 0)!=="production"&&r&&!w&&(console.warn("[DEPRECATED] Use `createWithEqualityFn` instead of `create` or use `useStoreWithEqualityFn` instead of `useStore`. They can be imported from 'zustand/traditional'. https://github.com/pmndrs/zustand/discussions/1937"),w=!0);const o=le(e.subscribe,e.getState,e.getServerState||e.getInitialState,t,r);return fe(o),o}const x=e=>{(T?"production":void 0)!=="production"&&typeof e!="function"&&console.warn("[DEPRECATED] Passing a vanilla store will be unsupported in a future version. Instead use `import { useStore } from 'zustand'`.");const t=typeof e=="function"?N(e):e,r=(o,n)=>ve(t,o,n);return Object.assign(r,t),r},Ee=e=>e?x(e):x;export{h as a,Ee as c,me as j};
