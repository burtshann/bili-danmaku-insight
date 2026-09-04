import React from "react";

export const Flow = (props) => {
  return (
    <div id="flow" className="text-center">
      <div className="container">
        <div className="col-md-8 col-md-offset-2 section-title">
          <h2>Flow Chart 流程图</h2>
          <p>
          </p>
        </div>
        <div id="row" >
          {props.data
            ? props.data.map((d, i) => (
                <div key={`${d.name}-${i}`} className="col-md-12 col-sm-12 team" >
                  <div className="thumbnail">
                    {" "}
                    <h4>{d.name}</h4>
                    <img src={d.img} alt="..." className="flow-img" />
                    <div className="caption">
                    </div>
                  </div>
                </div>
              ))
            : "loading"}
        </div>
      </div>
    </div>
  );
};
