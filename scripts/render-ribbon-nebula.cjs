'use strict';
// Offline original procedural artwork; no author code or shaders ship to the TV.
const fs = require('node:fs'),
  path = require('node:path');
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({
    headless: true,
    ...(process.env.BROWSER_CHANNEL
      ? { channel: process.env.BROWSER_CHANNEL }
      : {})
  });
  try {
    const p = await b.newPage({ viewport: { width: 1024, height: 576 } });
    await p.setContent('<canvas id="nebula"></canvas>');
    const result = await p.evaluate(() => {
      const c = document.getElementById('nebula');
      c.width = 4096;
      c.height = 2304;
      const gl = c.getContext('webgl', {
        alpha: false,
        antialias: false,
        preserveDrawingBuffer: true
      });
      if (!gl) throw Error('WebGL unavailable');
      const vertex = 'attribute vec2 p;void main(){gl_Position=vec4(p,0.,1.);}';
      const fragment = `precision highp float;
uniform vec2 resolution;
float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}
float noise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);return mix(mix(hash(i),hash(i+vec2(1,0)),f.x),mix(hash(i+vec2(0,1)),hash(i+vec2(1,1)),f.x),f.y);}
float fbm(vec2 p){float a=.5,v=0.;mat2 m=mat2(.8,-.6,.6,.8);for(int i=0;i<6;i++){v+=a*noise(p);p=m*p*2.03+17.7;a*=.5;}return v;}
void main(){
vec2 uv=gl_FragCoord.xy/resolution;vec2 p=(uv-vec2(.5,.59))*vec2(3.55,2.0);
vec2 w=vec2(fbm(p*2.8+2.2),fbm(p*2.8+8.9));
vec2 q=vec2(fbm(p*3.8+w*3.2+11.4),fbm(p*3.8+w*3.2-5.6));
float n=fbm(p*5.0+q*3.8+w*1.4);
float fine=fbm(p*30.+q*2.);
float ridge=pow(1.-abs(2.*fbm(p*8.+q*5.)-1.),7.);
float shape=exp(-pow(abs(p.x)/1.0,2.2)-pow(abs(p.y+.09*sin(p.x*3.))/0.40,2.));
float pockets=smoothstep(.32,.69,n);
float mist=shape*(.12+.88*pockets);
float filament=shape*pow(max(0.,n-.37)*3.,2.)*(.24+.76*ridge)*(.65+.35*fine);
float cyan=smoothstep(.4,.7,fbm(p*1.5+40.));
vec3 base=mix(vec3(.055,.025,.25),vec3(.015,.20,.52),cyan);
vec3 col=base*mist*.85+vec3(.04,.30,.67)*filament*.70;
col*=2.3;
col+=vec3(.10,.26,.43)*pow(min(filament*3.,1.),2.);
// Native-resolution sparse points, independent from the continuous gas density.
vec2 cell=floor(gl_FragCoord.xy/vec2(20.));vec2 st=fract(gl_FragCoord.xy/20.);
float pick=hash(cell+71.);vec2 centre=vec2(hash(cell+3.),hash(cell+29.))*.70+.15;
float d=length((st-centre)*20.);float star=exp(-d*d/1.1)*step(.978,pick);
float fade=smoothstep(0.,.15,uv.x)*smoothstep(0.,.15,1.-uv.x)*smoothstep(0.,.18,uv.y)*smoothstep(0.,.15,1.-uv.y);
col+=vec3(.60,.75,1.)*star*(.25+.60*hash(cell+11.))*fade;
col*=fade;col=max(col,vec3(0.));
// Fine dithering avoids large quantized bands in the faint blue haze.
col+=vec3((hash(gl_FragCoord.xy)-.5)/1024.)*step(.002,max(col.r,max(col.g,col.b)));
gl_FragColor=vec4(clamp(col,0.,1.),1.);
}`;
      function shader(type, src) {
        const s = gl.createShader(type);
        gl.shaderSource(s, src);
        gl.compileShader(s);
        if (!gl.getShaderParameter(s, gl.COMPILE_STATUS))
          throw Error(gl.getShaderInfoLog(s));
        return s;
      }
      const pr = gl.createProgram();
      gl.attachShader(pr, shader(gl.VERTEX_SHADER, vertex));
      gl.attachShader(pr, shader(gl.FRAGMENT_SHADER, fragment));
      gl.linkProgram(pr);
      if (!gl.getProgramParameter(pr, gl.LINK_STATUS))
        throw Error(gl.getProgramInfoLog(pr));
      gl.useProgram(pr);
      const buf = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, buf);
      gl.bufferData(
        gl.ARRAY_BUFFER,
        new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]),
        gl.STATIC_DRAW
      );
      const loc = gl.getAttribLocation(pr, 'p');
      gl.enableVertexAttribArray(loc);
      gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
      gl.uniform2f(gl.getUniformLocation(pr, 'resolution'), c.width, c.height);
      gl.viewport(0, 0, c.width, c.height);
      gl.drawArrays(gl.TRIANGLES, 0, 6);
      gl.finish();
      if (gl.getError() !== gl.NO_ERROR) throw Error('Render failed');
      return {
        data: c.toDataURL('image/png').split(',')[1],
        renderer: gl.getParameter(gl.RENDERER),
        width: c.width,
        height: c.height
      };
    });
    const out = path.resolve('build/ribbon-blue-nebula-original.png');
    fs.mkdirSync(path.dirname(out), { recursive: true });
    fs.writeFileSync(out, Buffer.from(result.data, 'base64'));
    delete result.data;
    console.log(out, result);
  } finally {
    await b.close();
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
