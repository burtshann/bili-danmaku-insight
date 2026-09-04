import React from "react";

export const Features = (props) => {
  return (
    <div id="features" className="text-center" >
      <div className="container">
        <div className="section-title">
        <br></br>
        <br></br>
          <h2>Features 功能</h2>
        </div>
        <div className="row">
          {props.data
            ? props.data.map((d, i) => (
                <div key={`${d.title}-${i}`} className="col-xs-6 col-md-3">
                  {" "}
                  <i className={d.icon}></i>
                  <h3>{d.title}</h3>
                  <p>{d.text}</p>
                  <br></br>
                  <br></br>
                </div>
              ))
            : "Loading..."}
        </div>
      </div>
    </div>
  );
};
