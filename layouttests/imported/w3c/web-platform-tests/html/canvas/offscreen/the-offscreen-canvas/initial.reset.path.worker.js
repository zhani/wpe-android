// DO NOT EDIT! This test has been generated by /html/canvas/tools/gentest.py.
// OffscreenCanvas test in a worker:initial.reset.path
// Description:Resetting the canvas state resets the current path
// Note:

importScripts("/resources/testharness.js");
importScripts("/html/canvas/resources/canvas-tests.js");

var t = async_test("Resetting the canvas state resets the current path");
var t_pass = t.done.bind(t);
var t_fail = t.step_func(function(reason) {
    throw reason;
});
t.step(function() {

  var canvas = new OffscreenCanvas(100, 50);
  var ctx = canvas.getContext('2d');

  canvas.width = 100;
  ctx.rect(0, 0, 100, 50);
  canvas.width = 100;
  ctx.fillStyle = '#f00';
  ctx.fill();
  _assertPixel(canvas, 20,20, 0,0,0,0);
  t.done();
});
done();
