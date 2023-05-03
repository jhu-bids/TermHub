import React, {useState, useEffect} from "react";
import {dataAccessor} from "./State";
import _ from "../supergroup/supergroup";
import * as d3Base from "d3";
import * as d3dag from "d3-dag";

const d3 = Object.assign({}, d3Base, d3dag);

export function currentConceptIds(props) {
  const concepts = props?.cset_data?.concepts ?? [];
  return concepts.map(c => c.concept_id);
}
export function ConceptGraph(props) {
  const {concept_ids, use_example=false} = props;
  const [concepts, setConcepts] = useState([]);
  const [edges, setEdges] = useState([]);
  const [edgeProps, setEdgeProps] = useState({parentProp:'sub', childProp:'obj'});
  const [svgSize, setSvgSize] = useState({width: 500, height: 500});
  const svg = React.useRef();

  console.log({concept_ids, concepts, props});
  window.d3 = d3;

  useEffect(() => {
    async function fetchData() {
      const _concepts = await dataAccessor.getConcepts(concept_ids, 'array');
      setConcepts(_concepts);
    }
    fetchData();
  }, []);
  useEffect(() => {
    async function fetchData() {
      if (use_example) {
        const ex = [{p:'a', c:'b'}, {p:'a', c:'c'}, {p:'a', c:'d'},
          {p:'b', c:'e'}, {p:'b', c:'f'},
          {p:'c', c:'f'},
          {p:'d', c:'g'},
          {p:'e', c:'h'},
          {p:'f', c:'h'}
        ]
        setEdges(ex);
        setEdgeProps({parentProp: 'p', childProp: 'c'});
        return;
      }
      const _edges = await dataAccessor.getSubgraphEdges(concept_ids, 'array');
      setEdges(_edges);
    }
    fetchData();
  }, []);
  useEffect(() => {
    if (!edges.length) {
      return;
    }
    const {width, height, dag } = drawGraph(svg, edges, edgeProps.parentProp, edgeProps.childProp);
    setSvgSize({width, height});
    window.dag = dag;
    window.svgcur = svg.current;
  }, [edges.length]);


  return (
      <div>
        <h3>d3 dag</h3>
        <svg
            ref={svg}
            id="svg"
            width={svgSize.width+200}
            height={svgSize.height+200}
        ></svg>
      </div>
  );
  // debugger;
  // let tree = _.hierarchicalTableToTree(edges, 'obj', 'sub')
  // let paths = tree.flattenTree().map(d => d.namePath());
  // console.log(paths);
  // return <pre>{paths.join('\n')}</pre>;
  // if (concepts.length) {
  //   // return <pre>{JSON.stringify(concepts, null, 2)}</pre>;
  // }
  // return <pre>{JSON.stringify(concept_ids)}</pre>;
}
function drawGraph(svg, edges, parentProp='sub', childProp = 'obj') {
  // edge looks like {
  //     "sub": "N3C:46274124",       // child
  //     "pred": "rdfs:subClassOf",
  //     "obj": "N3C:36684328",       // parent
  //     "meta": null
  //   },
  const edgeList = edges.map(d => [d[parentProp], d[childProp]])
  const connect = d3dag.dagConnect();
  const dag = connect(edgeList);
  /* from https://observablehq.com/@erikbrinkman/d3-dag-sugiyama */
  /*
  const coords = new Map([
    ["Simplex (medium)", d3.coordSimplex()],
    ["Quadratic (can be slow)", d3.coordQuad()],
    ["Greedy (fast)", d3.coordGreedy()],
    ["Center (fast)", d3.coordCenter()]
  ])
  const layerings = new Map([
      ["Simplex (shortest edges)", d3.layeringSimplex()],
      ["Longest Path (minimum height)", d3.layeringLongestPath()],
      ["Coffman Graham (constrained width)", d3.layeringCoffmanGraham()],
  ]
  */
  let nodeRadius = 20;
  let padding = 5;
  const base = nodeRadius * 2 * padding;

  const layout = d3
      .sugiyama()
      // .layering(d3.layeringSimplex())
      // .layering(d3.layeringCoffmanGraham())
      // .decross(d3.decrossTwoLayer().order(d3.twolayerAgg()))
      // .coord(d3.coordSimplex())
      .nodeSize(() => [2, 2])
      // .nodeSize((node) => {
      //   const size = node ? base : 5;
      //   return [1.2 * size, size];
      // })
  // const start = performance.now();
  // const time = performance.now() - start;
  // const layout = d3.sugiyama();

  const {width, height} = layout(dag);
  console.log(d3dag, dag, width, height, svg.current);

  // from https://observablehq.com/@bumbeishvili/d3-dag-vert
  const line = d3.line()
      .curve(d3.curveCatmullRom)
      .x(d => d.x*width)
      .y(d => d.y*height);

  const g = d3.select(svg.current).append('g').attr('transform',`translate(${100},${100})`);

  g.append('g')
      .selectAll('path')
      .data(dag.links())
      .enter()
      .append('path')
      .attr('d', ({ source, target, data }) =>
          line([
                 {
                   x: source.x,
                   y: source.y
                 }
               ].concat(
              data.points || [],
              [ {
                x: target.x,
                y: target.y
              }
              ])
          ))
      .attr('fill','none')
      .attr('stroke','black')
  console.log(g);

  const nodes = g.append('g')
      .selectAll('g')
      .data(dag.descendants())
      .enter()
      .append('g')
      .attr('transform', ({x, y}) => `translate(${x*width}, ${y*height})`);

  nodes.append('circle')
      .attr('r',3)
      .attr('fill','white')
      .attr('stroke','black')
  console.log(nodes);


  // Add text, which screws up measureement
  nodes.append('text').text(d => d.id).attr('text-anchor','middle').attr('alignment-baseline','middle');
  return {width, height, dag};
}
